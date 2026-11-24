"""Examination, registration, schedule and hall ticket schemas."""
from __future__ import annotations

from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import ExamType, PublicationStatus, RegistrationStatus


class ExaminationOut(BaseModel):
    id: UUID
    name: str
    exam_type: ExamType
    academic_year_id: UUID | None = None
    semester_id: UUID | None = None
    branch_id: UUID | None = None
    registration_start: datetime
    registration_deadline: datetime
    eligibility_criteria: dict
    status: str
    subject_ids: list[UUID] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ExaminationCreate(BaseModel):
    """Exam announcements are common to every branch and need no branch/semester tab.

    Any legacy ``branch_id``/``semester_id`` supplied by an old client is
    ignored; the server derives the semester from the attached subjects.
    """

    name: str
    exam_type: ExamType
    academic_year_id: UUID | None = None
    registration_start: datetime
    registration_deadline: datetime
    eligibility_criteria: dict = Field(default_factory=dict)
    subject_ids: list[UUID] = Field(default_factory=list)


class SubjectEligibilityOut(BaseModel):
    subject_id: UUID
    subject_code: str
    subject_name: str
    credits: int
    is_eligible: bool
    deadline: datetime
    already_registered: bool = False

    model_config = {"from_attributes": True}


class RegistrationOut(BaseModel):
    id: UUID
    examination_id: UUID
    examination_name: str | None = None
    exam_type: ExamType | None = None
    student_id: UUID
    status: RegistrationStatus
    submitted_at: datetime | None = None
    fee_receipt_filename: str | None = None
    fee_receipt_uploaded_at: datetime | None = None
    has_fee_receipt: bool = False
    subjects: list[dict] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class RegistrationCreate(BaseModel):
    examination_id: UUID
    subject_ids: list[UUID] = Field(min_length=1)


class ScheduleOut(BaseModel):
    id: UUID
    examination_id: UUID
    subject_id: UUID
    subject_code: str | None = None
    subject_name: str | None = None
    exam_date: date
    start_time: time
    end_time: time
    session: str | None = None
    venue: str | None = None
    publication_status: PublicationStatus

    model_config = {"from_attributes": True}


class ScheduleCreate(BaseModel):
    examination_id: UUID
    subject_id: UUID
    exam_date: date
    start_time: time
    end_time: time
    session: str | None = None
    venue: str | None = None


class HallTicketOut(BaseModel):
    id: UUID
    student_id: UUID
    examination_id: UUID
    ticket_number: str
    issued_at: datetime | None = None
    is_valid: bool

    model_config = {"from_attributes": True}
