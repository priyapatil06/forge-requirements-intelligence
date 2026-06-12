from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def uuid_str() -> str:
    return str(uuid.uuid4())


class ForgeSession(Base):
    __tablename__ = "forge_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    feature_name: Mapped[str] = mapped_column(String(200))
    feature_description: Mapped[str] = mapped_column(Text)
    business_objective: Mapped[str] = mapped_column(Text, default="")
    primary_actor: Mapped[str] = mapped_column(String(250), default="")
    data_inputs_outputs: Mapped[str] = mapped_column(Text, default="")
    downstream_dependencies: Mapped[str] = mapped_column(Text, default="")
    edge_cases: Mapped[str] = mapped_column(Text, default="")
    compliance_context: Mapped[str] = mapped_column(Text, default="")
    domain_pack: Mapped[str] = mapped_column(String(50), default="generic")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    runs: Mapped[list[ArtifactRun]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="ArtifactRun.created_at"
    )


class ArtifactRun(Base):
    __tablename__ = "artifact_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    session_id: Mapped[str] = mapped_column(ForeignKey("forge_sessions.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(30), default="completed")
    provider: Mapped[str] = mapped_column(String(50), default="mock")
    model: Mapped[str] = mapped_column(String(100), default="mock-forge-v1")
    prompt_version: Mapped[str] = mapped_column(String(30), default="1.0")
    artifacts: Mapped[dict[str, Any]] = mapped_column(JSON)
    latency_ms: Mapped[int | None] = mapped_column(default=None)
    error_message: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    session: Mapped[ForgeSession] = relationship(back_populates="runs")
    reviews: Mapped[list[ReviewAction]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="ReviewAction.created_at"
    )


class ReviewAction(Base):
    __tablename__ = "review_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    run_id: Mapped[str] = mapped_column(ForeignKey("artifact_runs.id", ondelete="CASCADE"))
    decision: Mapped[str] = mapped_column(String(30))
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    run: Mapped[ArtifactRun] = relationship(back_populates="reviews")


class JiraConnection(Base):
    __tablename__ = "jira_connections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    site_name: Mapped[str] = mapped_column(String(250))
    site_url: Mapped[str] = mapped_column(String(500))
    cloud_id: Mapped[str] = mapped_column(String(100), unique=True)
    access_token_encrypted: Mapped[str] = mapped_column(Text)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, default=None)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    scopes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class JiraOAuthState(Base):
    __tablename__ = "jira_oauth_states"

    state: Mapped[str] = mapped_column(String(200), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
