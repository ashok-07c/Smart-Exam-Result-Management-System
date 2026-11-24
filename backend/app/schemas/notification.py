"""Notification and audit schemas."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import AudienceType, NotificationCategory


class NotificationCreate(BaseModel):
    title: str
    message: str
    category: NotificationCategory
    audience_type: AudienceType = AudienceType.ALL
    branch_id: UUID | None = None
    semester_id: UUID | None = None
    academic_year_id: UUID | None = None
    section: str | None = None
    recipient_user_ids: list[UUID] | None = None
    publish: bool = True


class NotificationOut(BaseModel):
    id: UUID
    title: str
    message: str
    category: NotificationCategory
    sender_id: UUID
    audience_type: AudienceType
    created_at: datetime
    published_at: datetime | None = None
    read_at: datetime | None = None

    model_config = {"from_attributes": True}


class AuditOut(BaseModel):
    id: UUID
    user_id: UUID | None
    user_role: str | None
    action: str
    entity_type: str
    entity_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
