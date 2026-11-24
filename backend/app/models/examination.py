"""Examination, registration and scheduling models."""
from __future__ import annotations

import uuid
from datetime import date, datetime, time

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, Time, Uuid, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.common import TimestampMixin, uuid_pk
from app.models.enums import ExamType, PublicationStatus, RegistrationStatus


class Examination(Base, TimestampMixin):
    __tablename__ = "examinations"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    exam_type: Mapped[ExamType] = mapped_column(String(32), nullable=False, index=True)
    academic_year_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("academic_years.id"))
    semester_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("semesters.id"))
    branch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("branches.id"))
    registration_start: Mapped[datetime] = mapped_column(nullable=False)
    registration_deadline: Mapped[datetime] = mapped_column(nullable=False)
    eligibility_criteria: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="OPEN", nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"))

    subjects: Mapped[list["ExaminationSubject"]] = relationship(back_populates="examination", cascade="all, delete-orphan")


class ExaminationSubject(Base, TimestampMixin):
    __tablename__ = "examination_subjects"
    __table_args__ = (UniqueConstraint("examination_id", "subject_id", name="uq_exam_subject"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    examination_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("examinations.id", ondelete="CASCADE"), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("subjects.id"), nullable=False)
    is_eligible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    examination: Mapped[Examination] = relationship(back_populates="subjects")
    subject: Mapped["Subject"] = relationship()


class ExaminationEligibility(Base, TimestampMixin):
    """Explicit per-student eligibility override. Absence means criteria-based eligibility."""

    __tablename__ = "examination_eligibility"
    __table_args__ = (UniqueConstraint("examination_id", "student_id", name="uq_exam_student"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    examination_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("examinations.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("students.id"), nullable=False)
    is_eligible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500))


class ExaminationRegistration(Base, TimestampMixin):
    __tablename__ = "examination_registrations"
    __table_args__ = (UniqueConstraint("examination_id", "student_id", name="uq_registration"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    examination_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("examinations.id"), nullable=False, index=True)
    student_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("students.id"), nullable=False, index=True)
    status: Mapped[RegistrationStatus] = mapped_column(String(32), default=RegistrationStatus.SUBMITTED, nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column()
    fee_receipt_path: Mapped[str | None] = mapped_column(String(500))
    fee_receipt_filename: Mapped[str | None] = mapped_column(String(255))
    fee_receipt_content_type: Mapped[str | None] = mapped_column(String(100))
    fee_receipt_uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    examination: Mapped[Examination] = relationship()
    student: Mapped["Student"] = relationship()
    subjects: Mapped[list["RegistrationSubject"]] = relationship(back_populates="registration", cascade="all, delete-orphan")


class RegistrationSubject(Base, TimestampMixin):
    __tablename__ = "examination_registration_subjects"
    __table_args__ = (UniqueConstraint("registration_id", "subject_id", name="uq_reg_subject"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    registration_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("examination_registrations.id", ondelete="CASCADE"), nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("subjects.id"), nullable=False)
    registration: Mapped[ExaminationRegistration] = relationship(back_populates="subjects")
    subject: Mapped["Subject"] = relationship()


class ExamSession(Base, TimestampMixin):
    __tablename__ = "exam_sessions"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)


class ExaminationVenue(Base, TimestampMixin):
    __tablename__ = "examination_venues"

    id: Mapped[uuid.UUID] = uuid_pk()
    venue_name: Mapped[str] = mapped_column(String(200), nullable=False)
    capacity: Mapped[int | None] = mapped_column(Integer)


class ExaminationSchedule(Base, TimestampMixin):
    __tablename__ = "examination_schedules"

    id: Mapped[uuid.UUID] = uuid_pk()
    examination_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("examinations.id"), nullable=False, index=True)
    subject_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("subjects.id"), nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("branches.id"))
    semester_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("semesters.id"))
    academic_year_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("academic_years.id"))
    exam_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    session: Mapped[str | None] = mapped_column(String(64))
    venue: Mapped[str | None] = mapped_column(String(200))
    publication_status: Mapped[PublicationStatus] = mapped_column(
        String(32), default=PublicationStatus.DRAFT, nullable=False, index=True
    )
    change_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    examination: Mapped[Examination] = relationship()
    subject: Mapped["Subject"] = relationship()
