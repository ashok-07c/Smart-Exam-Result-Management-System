"""Marks and correction request schemas."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import CorrectionStatus, SubmissionStatus


class MarkEntryIn(BaseModel):
    student_id: UUID
    subject_id: UUID
    mid1_marks: float = Field(ge=0, le=25, description="MID-1 out of 25")
    mid2_marks: float = Field(ge=0, le=25, description="MID-2 out of 25")
    assignments_marks: float = Field(ge=0, le=5, description="Assignments out of 5")
    save_as_draft: bool = True


class BulkMarksIn(BaseModel):
    subject_id: UUID
    examination_id: UUID | None = None
    entries: list[MarkEntryIn]


class InternalMarkOut(BaseModel):
    id: UUID
    student_id: UUID
    subject_id: UUID
    subject_code: str | None = None
    subject_name: str | None = None
    student_name: str | None = None
    roll_number: str | None = None
    component_marks: dict
    mid1_marks: float = 0
    mid2_marks: float = 0
    assignments_marks: float = 0
    total_marks: float
    max_marks: int
    status: SubmissionStatus
    submitted_at: datetime | None = None

    model_config = {"from_attributes": True}


class MarksSubmissionOut(BaseModel):
    id: UUID
    faculty_id: UUID
    subject_id: UUID
    status: SubmissionStatus
    submitted_at: datetime | None = None
    review_note: str | None = None

    model_config = {"from_attributes": True}


class CorrectionCreate(BaseModel):
    """Plain-text / numeric correction request — no JSON fields."""

    subject_code: str = Field(min_length=1, max_length=64)
    reported_marks: float = Field(ge=0, le=1000)
    suggested_marks: float = Field(ge=0, le=1000)
    explanation: str = Field(min_length=5)


class CorrectionOut(BaseModel):
    id: UUID
    student_id: UUID
    subject_id: UUID
    student_name: str | None = None
    roll_number: str | None = None
    subject_code: str | None = None
    faculty_id: UUID | None = None
    reported_marks: float
    suggested_marks: float
    explanation: str
    request_status: CorrectionStatus
    faculty_response: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CorrectionReview(BaseModel):
    action: str = Field(pattern="^(approve|reject|under_review|correct)$")
    faculty_response: str | None = None
    corrected_marks: float | None = Field(default=None, ge=0)
