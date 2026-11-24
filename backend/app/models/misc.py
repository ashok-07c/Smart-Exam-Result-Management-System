"""Password reset tokens and hall tickets."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text, Uuid, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.common import TimestampMixin, uuid_pk


class PasswordResetToken(Base, TimestampMixin):
    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    used_at: Mapped[datetime | None] = mapped_column()
    requested_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))


class HallTicket(Base, TimestampMixin):
    __tablename__ = "hall_tickets"
    __table_args__ = (UniqueConstraint("student_id", "examination_id", name="uq_hall_ticket"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    student_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("students.id"), nullable=False, index=True)
    examination_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("examinations.id"), nullable=False)
    ticket_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    generated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    issued_at: Mapped[datetime | None] = mapped_column()

    examination: Mapped["Examination"] = relationship()
    student: Mapped["Student"] = relationship()
