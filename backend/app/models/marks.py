"""Internal marks, submissions and correction requests."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, ForeignKey, Integer, Numeric, String, Text, Uuid, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.common import TimestampMixin, uuid_pk
from app.models.enums import CorrectionStatus, SubmissionStatus


class InternalMark(Base, TimestampMixin):
    __tablename__ = "internal_marks"
    __table_args__ = (UniqueConstraint("student_id", "subject_id", "examination_id", name="uq_internal_mark"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    student_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("students.id"), nullable=False, index=True)
    subject_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("subjects.id"), nullable=False, index=True)
    examination_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("examinations.id"))
    faculty_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("faculty.id"))
    component_marks: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)  # {"MID-1": 20, ...}
    mid1_marks: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    mid2_marks: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    assignments_marks: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    total_marks: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=0)
    max_marks: Mapped[int] = mapped_column(Integer, nullable=False)
    academic_year_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("academic_years.id"))
    semester_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("semesters.id"))
    status: Mapped[SubmissionStatus] = mapped_column(String(32), default=SubmissionStatus.DRAFT, nullable=False, index=True)
    submitted_at: Mapped[datetime | None] = mapped_column()
    verified_at: Mapped[datetime | None] = mapped_column()
    verified_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    locked_at: Mapped[datetime | None] = mapped_column()

    student: Mapped["Student"] = relationship()
    subject: Mapped["Subject"] = relationship()
    components: Mapped[list["InternalMarkComponent"]] = relationship(
        back_populates="internal_mark", cascade="all, delete-orphan"
    )


class InternalMarkComponent(Base, TimestampMixin):
    __tablename__ = "internal_mark_components"
    __table_args__ = (UniqueConstraint("internal_mark_id", "name", name="uq_mark_component"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    internal_mark_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("internal_marks.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    marks_obtained: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    max_marks: Mapped[int] = mapped_column(Integer, nullable=False)

    internal_mark: Mapped[InternalMark] = relationship(back_populates="components")


class MarksSubmission(Base, TimestampMixin):
    __tablename__ = "marks_submissions"

    id: Mapped[uuid.UUID] = uuid_pk()
    faculty_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("faculty.id"), nullable=False, index=True)
    subject_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("subjects.id"), nullable=False)
    examination_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("examinations.id"))
    branch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("branches.id"))
    semester_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("semesters.id"))
    section: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[SubmissionStatus] = mapped_column(String(32), default=SubmissionStatus.DRAFT, nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column()
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    review_note: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column()

    subject: Mapped["Subject"] = relationship()
    faculty: Mapped["Faculty"] = relationship()


class StudentMarkCorrectionRequest(Base, TimestampMixin):
    __tablename__ = "student_mark_correction_requests"

    id: Mapped[uuid.UUID] = uuid_pk()
    student_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("students.id"), nullable=False, index=True)
    subject_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("subjects.id"), nullable=False)
    faculty_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("faculty.id"), index=True)
    subject_code: Mapped[str | None] = mapped_column(String(64))
    reported_marks: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)  # legacy; numeric value below is authoritative
    suggested_marks: Mapped[dict | None] = mapped_column(JSON)  # legacy; numeric value below is authoritative
    reported_marks_value: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=0)
    suggested_marks_value: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=0)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    request_status: Mapped[CorrectionStatus] = mapped_column(String(32), default=CorrectionStatus.SUBMITTED, nullable=False, index=True)
    faculty_response: Mapped[str | None] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column()

    student: Mapped["Student"] = relationship()
    subject: Mapped["Subject"] = relationship()
