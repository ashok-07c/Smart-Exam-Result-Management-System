"""Results, grades, backlogs and recounting models."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Numeric, String, Text, Uuid, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.common import TimestampMixin, uuid_pk
from app.models.enums import PublicationStatus, RecountingStatus, ResultStatus


class ExternalMark(Base, TimestampMixin):
    __tablename__ = "external_marks"
    __table_args__ = (UniqueConstraint("student_id", "subject_id", "examination_id", name="uq_external_mark"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    student_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("students.id"), nullable=False, index=True)
    subject_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("subjects.id"), nullable=False)
    examination_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("examinations.id"))
    marks_obtained: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=0)
    max_marks: Mapped[int] = mapped_column(Integer, nullable=False)
    entered_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))

    student: Mapped["Student"] = relationship()
    subject: Mapped["Subject"] = relationship()


class SemesterResult(Base, TimestampMixin):
    __tablename__ = "semester_results"
    __table_args__ = (
        UniqueConstraint("student_id", "academic_year_id", "semester_id", "examination_id", name="uq_semester_result"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    student_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("students.id"), nullable=False, index=True)
    academic_year_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("academic_years.id"))
    semester_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("semesters.id"))
    examination_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("examinations.id"))
    semester_number: Mapped[int] = mapped_column(Integer, nullable=False)
    academic_year_name: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    sgpa: Mapped[float | None] = mapped_column(Numeric(5, 2))
    cgpa: Mapped[float | None] = mapped_column(Numeric(5, 2))
    total_credits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    earned_credits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[PublicationStatus] = mapped_column(
        String(32), default=PublicationStatus.DRAFT, nullable=False, index=True
    )
    published_at: Mapped[datetime | None] = mapped_column()
    approved_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))
    certificate_reference: Mapped[str | None] = mapped_column(String(100), unique=True)

    subject_results: Mapped[list["SubjectResult"]] = relationship(back_populates="semester_result", cascade="all, delete-orphan")
    student: Mapped["Student"] = relationship()
    examination: Mapped["Examination"] = relationship()


class SubjectResult(Base, TimestampMixin):
    __tablename__ = "subject_results"
    __table_args__ = (UniqueConstraint("semester_result_id", "subject_id", name="uq_subject_result"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    semester_result_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("semester_results.id", ondelete="CASCADE"), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("subjects.id"), nullable=False)
    internal_marks: Mapped[float] = mapped_column(Numeric(6, 2), default=0, nullable=False)
    external_marks: Mapped[float] = mapped_column(Numeric(6, 2), default=0, nullable=False)
    total_marks: Mapped[float] = mapped_column(Numeric(6, 2), default=0, nullable=False)
    max_marks: Mapped[int] = mapped_column(Integer, nullable=False)
    credits: Mapped[int] = mapped_column(Integer, nullable=False)
    grade: Mapped[str] = mapped_column(String(8), nullable=False)
    grade_point: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    result_status: Mapped[ResultStatus] = mapped_column(String(16), nullable=False)

    semester_result: Mapped[SemesterResult] = relationship(back_populates="subject_results")
    subject: Mapped["Subject"] = relationship()


class Backlog(Base, TimestampMixin):
    __tablename__ = "backlogs"
    __table_args__ = (UniqueConstraint("student_id", "subject_id", name="uq_backlog"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    student_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("students.id"), nullable=False, index=True)
    subject_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("subjects.id"), nullable=False)
    semester_number: Mapped[int] = mapped_column(Integer, nullable=False)
    academic_year_name: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    attempts: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_cleared: Mapped[bool] = mapped_column(default=False, nullable=False)
    cleared_at: Mapped[datetime | None] = mapped_column()
    cleared_by_result_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("semester_results.id"))
    supplementary_exam_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("examinations.id"))

    student: Mapped["Student"] = relationship()
    subject: Mapped["Subject"] = relationship()


class ExternalMarkImport(Base, TimestampMixin):
    """A validated CSV staging record awaiting explicit admin confirmation."""

    __tablename__ = "external_mark_imports"

    id: Mapped[uuid.UUID] = uuid_pk()
    admin_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    examination_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("examinations.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    rows: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RecountingRequest(Base, TimestampMixin):
    __tablename__ = "recounting_requests"
    __table_args__ = (UniqueConstraint("student_id", "examination_id", "subject_id", name="uq_recounting"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    student_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("students.id"), nullable=False, index=True)
    examination_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("examinations.id"), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("subjects.id"), nullable=False)
    original_marks: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    request_status: Mapped[RecountingStatus] = mapped_column(String(32), default=RecountingStatus.SUBMITTED, nullable=False, index=True)
    admin_response: Mapped[str | None] = mapped_column(Text)
    revised_marks: Mapped[float | None] = mapped_column(Numeric(6, 2))
    completed_at: Mapped[datetime | None] = mapped_column()
    processed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))

    student: Mapped["Student"] = relationship()
    subject: Mapped["Subject"] = relationship()
    examination: Mapped["Examination"] = relationship()
    history: Mapped[list["RecountingRequestHistory"]] = relationship(back_populates="request", cascade="all, delete-orphan")


class RecountingRequestHistory(Base, TimestampMixin):
    __tablename__ = "recounting_request_history"

    id: Mapped[uuid.UUID] = uuid_pk()
    request_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("recounting_requests.id", ondelete="CASCADE"), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(32))
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))

    request: Mapped[RecountingRequest] = relationship(back_populates="history")
