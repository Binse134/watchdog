import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True


class ConnectionCreate(BaseModel):
    n8n_base_url: str
    api_key: str


class ConnectionUpdate(BaseModel):
    n8n_base_url: str | None = None
    api_key: str | None = None


class ConnectionOut(BaseModel):
    id: uuid.UUID
    n8n_base_url: str
    last_sync_status: str
    last_sync_error: str | None
    last_sync_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class WorkflowOut(BaseModel):
    id: uuid.UUID
    n8n_workflow_id: str
    name: str
    enabled: bool
    last_synced_at: datetime | None
    health_status: str
    run_count_7d: int
    error_count_7d: int
    run_count_30d: int
    error_count_30d: int
    summary: str | None
    summary_generated_at: datetime | None


class SyncResult(BaseModel):
    workflows_synced: int
    executions_synced: int
    last_sync_status: str
    last_sync_error: str | None
    last_sync_at: datetime | None


class WorkflowSummaryOut(BaseModel):
    workflow_id: uuid.UUID
    summary: str
    generated_at: datetime

    class Config:
        from_attributes = True


class AlertOut(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    workflow_name: str
    alert_type: str
    triggered_at: datetime
    resolved_at: datetime | None
    email_sent_at: datetime | None
    email_error: str | None
