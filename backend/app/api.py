from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse, Response, StreamingResponse
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.config import Settings, get_settings
from app.database import get_db
from app.domain_packs import DOMAIN_PACKS
from app.exporters import export_zip, json_bundle, mermaid_state_machine, openapi_yaml
from app.jira import complete_oauth, list_projects, oauth_authorization_url, sync_run_to_jira
from app.llm import generate_artifacts
from app.models import ArtifactRun, ForgeSession, JiraConnection, ReviewAction
from app.schemas import (
    ArtifactRunRead,
    ArtifactSet,
    ArtifactUpdate,
    ForgeSessionCreate,
    ForgeSessionRead,
    ForgeSessionUpdate,
    JiraSyncRequest,
    JiraSyncResult,
    ReviewActionCreate,
)

router = APIRouter(prefix="/api/v1")


def _session_or_404(db: Session, session_id: str) -> ForgeSession:
    row = db.scalar(
        select(ForgeSession)
        .where(ForgeSession.id == session_id)
        .options(selectinload(ForgeSession.runs).selectinload(ArtifactRun.reviews))
    )
    if not row:
        raise HTTPException(status_code=404, detail="Session not found.")
    return row


def _run_or_404(db: Session, run_id: str) -> ArtifactRun:
    row = db.scalar(
        select(ArtifactRun)
        .where(ArtifactRun.id == run_id)
        .options(selectinload(ArtifactRun.reviews), selectinload(ArtifactRun.session))
    )
    if not row:
        raise HTTPException(status_code=404, detail="Artifact run not found.")
    return row


@router.get("/health")
def health(settings: Settings = Depends(get_settings)) -> dict[str, object]:
    return {"status": "ok", "mock_llm": settings.forge_mock_llm}


@router.get("/domain-packs")
def domain_packs() -> list[dict[str, object]]:
    return [{"id": key, **value} for key, value in DOMAIN_PACKS.items()]


@router.post("/sessions", response_model=ForgeSessionRead, status_code=201)
def create_session(payload: ForgeSessionCreate, db: Session = Depends(get_db)) -> ForgeSession:
    row = ForgeSession(**payload.model_dump(mode="json"))
    db.add(row)
    db.commit()
    return _session_or_404(db, row.id)


@router.get("/sessions", response_model=list[ForgeSessionRead])
def list_sessions(
    limit: int = Query(default=30, ge=1, le=100), db: Session = Depends(get_db)
) -> list[ForgeSession]:
    return list(
        db.scalars(
            select(ForgeSession)
            .options(selectinload(ForgeSession.runs).selectinload(ArtifactRun.reviews))
            .order_by(desc(ForgeSession.updated_at))
            .limit(limit)
        ).all()
    )


@router.get("/sessions/{session_id}", response_model=ForgeSessionRead)
def get_session(session_id: str, db: Session = Depends(get_db)) -> ForgeSession:
    return _session_or_404(db, session_id)


@router.patch("/sessions/{session_id}", response_model=ForgeSessionRead)
def update_session(
    session_id: str, payload: ForgeSessionUpdate, db: Session = Depends(get_db)
) -> ForgeSession:
    row = _session_or_404(db, session_id)
    for key, value in payload.model_dump(exclude_unset=True, mode="json").items():
        setattr(row, key, value)
    row.updated_at = datetime.now(timezone.utc)
    db.add(row)
    db.commit()
    return _session_or_404(db, session_id)


@router.post("/sessions/{session_id}/generate", response_model=ArtifactRunRead, status_code=201)
def generate(
    session_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ArtifactRun:
    forge_session = _session_or_404(db, session_id)
    try:
        result = generate_artifacts(forge_session, settings)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Artifact generation failed: {exc}") from exc

    run = ArtifactRun(
        session_id=forge_session.id,
        status="completed",
        provider=result.provider,
        model=result.model,
        prompt_version=result.prompt_version,
        artifacts=result.artifacts.model_dump(by_alias=True),
        latency_ms=result.latency_ms,
    )
    db.add(run)
    db.commit()
    return _run_or_404(db, run.id)


@router.get("/runs/{run_id}", response_model=ArtifactRunRead)
def get_run(run_id: str, db: Session = Depends(get_db)) -> ArtifactRun:
    return _run_or_404(db, run_id)


@router.put("/runs/{run_id}", response_model=ArtifactRunRead)
def update_run(
    run_id: str, payload: ArtifactUpdate, db: Session = Depends(get_db)
) -> ArtifactRun:
    row = _run_or_404(db, run_id)
    row.artifacts = payload.artifacts.model_dump(by_alias=True)
    row.status = "edited"
    db.add(row)
    db.commit()
    return _run_or_404(db, run_id)


@router.post("/runs/{run_id}/review", response_model=ArtifactRunRead, status_code=201)
def review_run(
    run_id: str, payload: ReviewActionCreate, db: Session = Depends(get_db)
) -> ArtifactRun:
    row = _run_or_404(db, run_id)
    db.add(ReviewAction(run_id=row.id, **payload.model_dump()))
    if payload.decision == "approved":
        row.status = "approved"
    elif payload.decision == "changes_requested":
        row.status = "changes_requested"
    db.add(row)
    db.commit()
    return _run_or_404(db, run_id)


@router.get("/runs/{run_id}/export")
def export_run(
    run_id: str,
    format: Literal["json", "openapi", "mermaid", "zip"] = "json",
    db: Session = Depends(get_db),
) -> Response:
    run = _run_or_404(db, run_id)
    forge_session = run.session
    artifacts = ArtifactSet.model_validate(run.artifacts)
    safe_name = "-".join(forge_session.feature_name.lower().split())[:60] or "forge"
    if format == "json":
        return Response(
            json_bundle(forge_session, run),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}.json"'},
        )
    if format == "openapi":
        return Response(
            openapi_yaml(artifacts, forge_session.feature_name),
            media_type="application/yaml",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}-openapi.yaml"'},
        )
    if format == "mermaid":
        return Response(
            mermaid_state_machine(artifacts),
            media_type="text/plain",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}-state-machine.mmd"'},
        )
    data = export_zip(forge_session, run, artifacts)
    return StreamingResponse(
        BytesIO(data),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}-forge-bundle.zip"'},
    )


@router.get("/jira/status")
def jira_status(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> dict[str, object]:
    connections = list(db.scalars(select(JiraConnection).order_by(desc(JiraConnection.updated_at))).all())
    return {
        "configured": bool(settings.atlassian_client_id and settings.atlassian_client_secret),
        "connections": [
            {
                "id": item.id,
                "site_name": item.site_name,
                "site_url": item.site_url,
                "cloud_id": item.cloud_id,
            }
            for item in connections
        ],
    }


@router.get("/jira/oauth/start")
def jira_oauth_start(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> dict[str, str]:
    try:
        return {"authorization_url": oauth_authorization_url(db, settings)}
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/jira/callback")
def jira_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    try:
        connection = complete_oauth(db, settings, code, state)
    except Exception as exc:
        return RedirectResponse(
            f"{settings.forge_frontend_url}?jira=error&message={str(exc)}", status_code=302
        )
    return RedirectResponse(
        f"{settings.forge_frontend_url}?jira=connected&connection={connection.id}",
        status_code=302,
    )


@router.get("/jira/connections/{connection_id}/projects")
def jira_projects(
    connection_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[dict[str, object]]:
    connection = db.get(JiraConnection, connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Jira connection not found.")
    try:
        return list_projects(db, settings, connection)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Jira project lookup failed: {exc}") from exc


@router.post("/runs/{run_id}/jira-sync", response_model=JiraSyncResult)
def jira_sync(
    run_id: str,
    payload: JiraSyncRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> JiraSyncResult:
    run = _run_or_404(db, run_id)
    connection = db.get(JiraConnection, payload.connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Jira connection not found.")
    try:
        created, warnings = sync_run_to_jira(db, settings, connection, run, payload.mapping)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Jira synchronization failed: {exc}") from exc
    return JiraSyncResult(created_issues=created, warnings=warnings)
