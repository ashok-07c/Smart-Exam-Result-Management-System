"""Notifications, recipients and audit log."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.common import TimestampMixin, uuid_pk
from app.models.enums import AudienceType, NotificationCategory


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = uuid_pk()
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[NotificationCategory] = mapped_column(String(48), nullable=False, index=True)
    sender_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    audience_type: Mapped[AudienceType] = mapped_column(String(48), nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("branches.id"))
    semester_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("semesters.id"))
    academic_year_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("academic_years.id"))
    section: Mapped[str | None] = mapped_column(String(32))
    published_at: Mapped[datetime | None] = mapped_column(index=True)

    recipients: Mapped[list["NotificationRecipient"]] = relationship(back_populates="notification", cascade="all, delete-orphan")


class NotificationRecipient(Base, TimestampMixin):
    __tablename__ = "notification_recipients"

    id: Mapped[uuid.UUID] = uuid_pk()
    notification_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient_user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    read_at: Mapped[datetime | None] = mapped_column()

    notification: Mapped[Notification] = relationship(back_populates="recipients")


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    user_role: Mapped[str | None] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(100))
    previous_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    request_context: Mapped[str | None] = mapped_column(Text)
