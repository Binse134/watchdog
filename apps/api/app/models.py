import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Boolean, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    connections: Mapped[list["Connection"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Connection(Base):
    __tablename__ = "connections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    n8n_base_url: Mapped[str] = mapped_column(String, nullable=False)
    api_key_encrypted: Mapped[str] = mapped_column(String, nullable=False)

    # "never" | "ok" | "error" | "unauthorized"
    last_sync_status: Mapped[str] = mapped_column(String, default="never", nullable=False)
    last_sync_error: Mapped[str | None] = mapped_column(String, nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    user: Mapped["User"] = relationship(back_populates="connections")
    workflows: Mapped[list["Workflow"]] = relationship(back_populates="connection", cascade="all, delete-orphan")


class Workflow(Base):
    __tablename__ = "workflows"
    __table_args__ = (UniqueConstraint("connection_id", "n8n_workflow_id", name="uq_workflow_connection_n8n_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("connections.id", ondelete="CASCADE"), nullable=False)
    n8n_workflow_id: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # True once a sync no longer finds this workflow in n8n's workflow list
    # (deleted there). We keep the row - and its history/alerts - instead of
    # deleting it.
    is_orphaned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    connection: Mapped["Connection"] = relationship(back_populates="workflows")
    executions: Mapped[list["Execution"]] = relationship(back_populates="workflow", cascade="all, delete-orphan")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="workflow", cascade="all, delete-orphan")
    summary: Mapped["WorkflowSummary | None"] = relationship(
        back_populates="workflow", cascade="all, delete-orphan", uselist=False
    )


class Execution(Base):
    __tablename__ = "executions"
    __table_args__ = (UniqueConstraint("workflow_id", "n8n_execution_id", name="uq_execution_workflow_n8n_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    n8n_execution_id: Mapped[str] = mapped_column(String, nullable=False)

    # n8n execution status: success | error | crashed | running | waiting | new | canceled | unknown
    status: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    workflow: Mapped["Workflow"] = relationship(back_populates="executions")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)

    # "failing" | "silent" | "orphaned" - mirrors app.health.ALERTABLE_STATUSES
    alert_type: Mapped[str] = mapped_column(String, nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    # NULL while the condition is still active; set once health recovers.
    # An unresolved row is what dedupes repeat emails for the same incident.
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    email_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    email_error: Mapped[str | None] = mapped_column(String, nullable=True)

    workflow: Mapped["Workflow"] = relationship(back_populates="alerts")


class WorkflowSummary(Base):
    __tablename__ = "workflow_summaries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    # sha256 of the workflow's nodes+connections (position/ids excluded) at
    # generation time. A mismatch means the workflow changed in n8n since -
    # this is the entire cache invalidation mechanism, see app/summaries.py.
    definition_hash: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    workflow: Mapped["Workflow"] = relationship(back_populates="summary")
