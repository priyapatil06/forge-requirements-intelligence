from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import ArtifactRun, JiraConnection, JiraOAuthState
from app.schemas import ArtifactSet, JiraFieldMapping
from app.security import TokenCipher

AUTH_URL = "https://auth.atlassian.com/authorize"
TOKEN_URL = "https://auth.atlassian.com/oauth/token"
RESOURCES_URL = "https://api.atlassian.com/oauth/token/accessible-resources"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def oauth_authorization_url(db: Session, settings: Settings) -> str:
    if not settings.atlassian_client_id or not settings.atlassian_client_secret:
        raise RuntimeError("Atlassian OAuth is not configured.")
    state = secrets.token_urlsafe(32)
    db.add(JiraOAuthState(state=state, expires_at=_now() + timedelta(minutes=10)))
    db.commit()
    params = {
        "audience": "api.atlassian.com",
        "client_id": settings.atlassian_client_id,
        "scope": settings.atlassian_scopes,
        "redirect_uri": settings.atlassian_redirect_uri,
        "state": state,
        "response_type": "code",
        "prompt": "consent",
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def complete_oauth(db: Session, settings: Settings, code: str, state: str) -> JiraConnection:
    state_row = db.get(JiraOAuthState, state)
    if not state_row or state_row.expires_at < _now():
        raise ValueError("OAuth state is missing or expired.")
    db.delete(state_row)
    db.commit()

    with httpx.Client(timeout=30) as client:
        token_response = client.post(
            TOKEN_URL,
            json={
                "grant_type": "authorization_code",
                "client_id": settings.atlassian_client_id,
                "client_secret": settings.atlassian_client_secret,
                "code": code,
                "redirect_uri": settings.atlassian_redirect_uri,
            },
        )
        token_response.raise_for_status()
        token = token_response.json()
        access_token = token["access_token"]
        resources_response = client.get(
            RESOURCES_URL,
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        )
        resources_response.raise_for_status()
        resources = resources_response.json()

    if not resources:
        raise ValueError("No Jira Cloud site was authorized.")
    resource = resources[0]
    cipher = TokenCipher(settings)
    existing = db.scalar(select(JiraConnection).where(JiraConnection.cloud_id == resource["id"]))
    connection = existing or JiraConnection(
        site_name=resource.get("name", "Jira Cloud"),
        site_url=resource.get("url", ""),
        cloud_id=resource["id"],
        access_token_encrypted="",
    )
    connection.site_name = resource.get("name", connection.site_name)
    connection.site_url = resource.get("url", connection.site_url)
    connection.access_token_encrypted = cipher.encrypt(access_token)
    refresh_token = token.get("refresh_token")
    if refresh_token:
        connection.refresh_token_encrypted = cipher.encrypt(refresh_token)
    connection.expires_at = _now() + timedelta(seconds=int(token.get("expires_in", 3600)))
    connection.scopes = token.get("scope", settings.atlassian_scopes)
    db.add(connection)
    db.commit()
    db.refresh(connection)
    return connection


def _access_token(db: Session, settings: Settings, connection: JiraConnection) -> str:
    cipher = TokenCipher(settings)
    if connection.expires_at and connection.expires_at > _now() + timedelta(seconds=90):
        return cipher.decrypt(connection.access_token_encrypted)
    if not connection.refresh_token_encrypted:
        raise RuntimeError("Jira access token expired and no refresh token is available.")

    refresh_token = cipher.decrypt(connection.refresh_token_encrypted)
    response = httpx.post(
        TOKEN_URL,
        timeout=30,
        json={
            "grant_type": "refresh_token",
            "client_id": settings.atlassian_client_id,
            "client_secret": settings.atlassian_client_secret,
            "refresh_token": refresh_token,
        },
    )
    response.raise_for_status()
    token = response.json()
    connection.access_token_encrypted = cipher.encrypt(token["access_token"])
    if token.get("refresh_token"):
        connection.refresh_token_encrypted = cipher.encrypt(token["refresh_token"])
    connection.expires_at = _now() + timedelta(seconds=int(token.get("expires_in", 3600)))
    db.add(connection)
    db.commit()
    return token["access_token"]


def _api_url(connection: JiraConnection, path: str) -> str:
    return f"https://api.atlassian.com/ex/jira/{connection.cloud_id}/rest/api/3{path}"


def list_projects(db: Session, settings: Settings, connection: JiraConnection) -> list[dict[str, Any]]:
    token = _access_token(db, settings, connection)
    response = httpx.get(
        _api_url(connection, "/project/search?maxResults=100"),
        timeout=30,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    response.raise_for_status()
    return response.json().get("values", [])


def _adf_description(ticket: dict[str, Any]) -> dict[str, Any]:
    content: list[dict[str, Any]] = [
        {
            "type": "paragraph",
            "content": [{"type": "text", "text": ticket["story"]}],
        },
        {
            "type": "heading",
            "attrs": {"level": 3},
            "content": [{"type": "text", "text": "Acceptance criteria"}],
        },
    ]
    for criterion in ticket["acceptance_criteria"]:
        content.append(
            {
                "type": "bulletList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": criterion}],
                            }
                        ],
                    }
                ],
            }
        )
    content.append(
        {
            "type": "paragraph",
            "content": [
                {
                    "type": "text",
                    "text": "Generated by Forge. Human review required.",
                    "marks": [{"type": "em"}],
                }
            ],
        }
    )
    return {"type": "doc", "version": 1, "content": content}


def _issue_type(ticket_type: str, mapping: JiraFieldMapping) -> str:
    return {
        "Story": mapping.story_issue_type,
        "Task": mapping.task_issue_type,
        "Bug": mapping.bug_issue_type,
    }[ticket_type]


def _create_issue(
    token: str,
    connection: JiraConnection,
    fields: dict[str, Any],
) -> dict[str, Any]:
    response = httpx.post(
        _api_url(connection, "/issue"),
        timeout=30,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        json={"fields": fields},
    )
    response.raise_for_status()
    return response.json()


def sync_run_to_jira(
    db: Session,
    settings: Settings,
    connection: JiraConnection,
    run: ArtifactRun,
    mapping: JiraFieldMapping,
) -> tuple[list[dict[str, Any]], list[str]]:
    artifacts = ArtifactSet.model_validate(run.artifacts)
    token = _access_token(db, settings, connection)
    created: list[dict[str, Any]] = []
    warnings: list[str] = []
    epic_key: str | None = None

    if mapping.create_epic:
        epic_fields: dict[str, Any] = {
            "project": {"key": mapping.project_key},
            "issuetype": {"name": mapping.epic_issue_type},
            "summary": artifacts.summary[:250],
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": artifacts.summary}],
                    }
                ],
            },
            "labels": list(dict.fromkeys(mapping.labels + ["forge-epic"])),
        }
        if mapping.epic_name_field:
            epic_fields[mapping.epic_name_field] = artifacts.summary[:250]
        epic = _create_issue(token, connection, epic_fields)
        epic_key = epic.get("key")
        created.append(epic)

    for ticket in artifacts.jira_tickets:
        fields: dict[str, Any] = {
            "project": {"key": mapping.project_key},
            "issuetype": {"name": _issue_type(ticket.type, mapping)},
            "summary": ticket.title[:250],
            "description": _adf_description(ticket.model_dump()),
            "labels": list(dict.fromkeys(mapping.labels + ticket.labels)),
        }
        if mapping.story_points_field:
            fields[mapping.story_points_field] = ticket.story_points
        if epic_key:
            fields[mapping.parent_field] = {"key": epic_key}
        try:
            issue = _create_issue(token, connection, fields)
            created.append(issue)
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:1000]
            warnings.append(f"Failed to create '{ticket.title}': {detail}")
    return created, warnings
