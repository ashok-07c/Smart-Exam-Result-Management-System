"""Examination Admin: examinations, registrations, schedules, timetables, hall tickets, notifications."""
from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, DbSession, ExamAdmin, get_or_404
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.core.responses import ok
from app.core.config import settings
from app.models.academic import Course, Semester, Subject
from app.models.enums import ExamType, NotificationCategory, PublicationStatus, RegistrationStatus, Role
from app.models.examination import (
    Examination,
    ExaminationRegistration,
    ExaminationSchedule,
    ExaminationSubject,
)
from app.models.misc import HallTicket
from app.models.notification import Notification
from app.models.user import Student, User
from app.schemas.examination import ExaminationCreate, ScheduleCreate
from app.schemas.notification import NotificationCreate
from app.services.audit import log_action
from app.services.notifications import create_notification
from app.utils.pdf import render_timetable

router = APIRouter()


def _exam_out(exam: Examination) -> dict:
    return {
        "id": exam.id,
        "name": exam.name,
        "exam_type": exam.exam_type,
        "academic_year_id": exam.academic_year_id,
        "semester_id": exam.semester_id,
        # Announcements are common to all branches; legacy rows are reported as
        # branchless so clients cannot reintroduce a branch filter.
        "branch_id": None,
        "registration_start": exam.registration_start,
        "registration_deadline": exam.registration_deadline,
        "eligibility_criteria": exam.eligibility_criteria,
        "status": exam.status,
        "subject_ids": [es.subject_id for es in exam.subjects],
    }


COMMON_EXAM_CRITERIA_KEYS = {"eligible_branches", "eligible_semesters", "min_semester"}


def _common_exam_data(db: Session, payload: ExaminationCreate) -> dict:
    """Build exam fields without any client-supplied branch or semester."""
    data = payload.model_dump(exclude={"subject_ids"}, exclude_none=False)
    data["branch_id"] = None
    criteria = dict(payload.eligibility_criteria or {})
    for key in COMMON_EXAM_CRITERIA_KEYS:
        criteria.pop(key, None)
    data["eligibility_criteria"] = criteria
    semesters = {
        subject.semester_id
        for subject in (db.get(Subject, subject_id) for subject_id in payload.subject_ids)
        if subject and subject.semester_id
    }
    data["semester_id"] = next(iter(semesters)) if len(semesters) == 1 else None
    return data


@router.get("/examinations")
def list_examinations(admin: ExamAdmin, db: DbSession, exam_type: ExamType | None = None) -> dict:
    query = db.query(Examination)
    if exam_type:
        query = query.filter(Examination.exam_type == exam_type)
    return ok([_exam_out(e) for e in query.order_by(Examination.registration_deadline).all()], "Examinations")


@router.post("/examinations")
def create_examination(payload: ExaminationCreate, admin: ExamAdmin, db: DbSession) -> dict:
    if payload.registration_deadline <= payload.registration_start:
        raise ValidationError("Registration deadline must be after the start date")
    if db.query(Examination).filter_by(name=payload.name).first():
        raise ConflictError("An examination with this name already exists")
    data = _common_exam_data(db, payload)
    exam = Examination(**data, created_by=admin.id)
    db.add(exam)
    db.flush()
    for subject_id in payload.subject_ids:
        if not db.get(Subject, subject_id):
            raise ValidationError(f"Subject {subject_id} does not exist")
        db.add(ExaminationSubject(examination_id=exam.id, subject_id=subject_id))
    log_action(db, user=admin, action="EXAMINATION_CREATED", entity_type="Examination", entity_id=str(exam.id), new=payload.model_dump())
    db.commit()
    return ok({"id": exam.id}, "Examination created")


@router.get("/examinations/{examination_id}")
def get_examination(examination_id: UUID, admin: ExamAdmin, db: DbSession) -> dict:
    return ok(_exam_out(get_or_404(db, Examination, examination_id)), "Examination")


@router.patch("/examinations/{examination_id}")
def update_examination(examination_id: UUID, payload: ExaminationCreate, admin: ExamAdmin, db: DbSession) -> dict:
    exam = get_or_404(db, Examination, examination_id)
    if payload.registration_deadline <= payload.registration_start:
        raise ValidationError("Registration deadline must be after the start date")
    previous = _exam_out(exam)
    for field, value in _common_exam_data(db, payload).items():
        setattr(exam, field, value)
    if payload.subject_ids is not None:
        db.query(ExaminationSubject).filter_by(examination_id=exam.id).delete()
        for subject_id in payload.subject_ids:
            db.add(ExaminationSubject(examination_id=exam.id, subject_id=subject_id))
    log_action(db, user=admin, action="EXAMINATION_UPDATED", entity_type="Examination", entity_id=str(examination_id), previous=previous)
    db.commit()
    return ok(message="Examination updated")


@router.get("/registrations")
def list_registrations(
    admin: ExamAdmin, db: DbSession, examination_id: UUID | None = None,
    status: RegistrationStatus | None = None, page: int = 1, page_size: int = 20,
) -> dict:
    query = db.query(ExaminationRegistration)
    if examination_id:
        query = query.filter(ExaminationRegistration.examination_id == examination_id)
    if status:
        query = query.filter(ExaminationRegistration.status == status)
    total = query.count()
    page = max(1, page)
    page_size = max(1, min(200, page_size))
    rows = query.order_by(ExaminationRegistration.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return ok({
        "items": [
            {
                "id": r.id, "examination_id": r.examination_id, "examination_name": r.examination.name,
                "student_id": r.student_id, "student_name": r.student.full_name,
                "roll_number": r.student.roll_number, "status": r.status, "submitted_at": r.submitted_at,
                "has_fee_receipt": bool(r.fee_receipt_path),
                "fee_receipt_filename": r.fee_receipt_filename,
                "subjects": [{"subject_code": rs.subject.subject_code, "subject_name": rs.subject.subject_name} for rs in r.subjects],
            }
            for r in rows
        ],
        "total": total, "page": page, "page_size": page_size,
        "pages": max(1, (total + page_size - 1) // page_size),
    }, "Registrations")


@router.patch("/registrations/{registration_id}")
def update_registration(registration_id: UUID, status: RegistrationStatus, admin: ExamAdmin, db: DbSession) -> dict:
    registration = get_or_404(db, ExaminationRegistration, registration_id)
    registration.status = status
    log_action(db, user=admin, action="REGISTRATION_STATUS_CHANGED", entity_type="ExaminationRegistration", entity_id=str(registration_id), new={"status": status})
    db.commit()
    return ok(message="Registration status updated")


@router.get("/registrations/{registration_id}/receipt")
def download_registration_receipt(registration_id: UUID, admin: ExamAdmin, db: DbSession) -> Response:
    registration = get_or_404(db, ExaminationRegistration, registration_id)
    if not registration.fee_receipt_path:
        raise NotFoundError("Fee receipt not found")
    from app.utils.uploads import receipt_path

    path = receipt_path(registration.fee_receipt_path)
    from fastapi.responses import FileResponse

    return FileResponse(
        path,
        media_type=registration.fee_receipt_content_type or "application/pdf",
        filename=registration.fee_receipt_filename or "fee-receipt",
    )


@router.get("/notifications")
def list_notifications(admin: ExamAdmin, db: DbSession) -> dict:
    rows = db.query(Notification).order_by(Notification.created_at.desc()).limit(100).all()
    return ok([
        {
            "id": n.id, "title": n.title, "message": n.message, "category": n.category,
            "audience_type": n.audience_type, "created_at": n.created_at, "published_at": n.published_at,
        }
        for n in rows
    ], "Notifications")


@router.post("/notifications")
def publish_notification(payload: NotificationCreate, admin: ExamAdmin, db: DbSession) -> dict:
    notification = create_notification(db, payload, admin)
    log_action(db, user=admin, action="NOTIFICATION_PUBLISHED", entity_type="Notification", entity_id=str(notification.id), new=payload.model_dump())
    db.commit()
    return ok({"id": notification.id, "recipient_count": len(notification.recipients)}, "Notification published")


@router.get("/schedules")
def list_schedules(admin: ExamAdmin, db: DbSession, examination_id: UUID | None = None) -> dict:
    query = db.query(ExaminationSchedule)
    if examination_id:
        query = query.filter(ExaminationSchedule.examination_id == examination_id)
    rows = query.order_by(ExaminationSchedule.exam_date, ExaminationSchedule.start_time).all()
    return ok([
        {
            "id": s.id, "examination_id": s.examination_id, "examination_name": s.examination.name,
            "subject_id": s.subject_id, "subject_code": s.subject.subject_code,
            "subject_name": s.subject.subject_name, "exam_date": s.exam_date.isoformat(),
            "start_time": s.start_time.strftime("%H:%M"), "end_time": s.end_time.strftime("%H:%M"),
            "session": s.session, "venue": s.venue, "publication_status": s.publication_status,
        }
        for s in rows
    ], "Examination schedules")


def _schedule_scope(db: Session, payload: ScheduleCreate) -> dict:
    """Derive branch/semester from the selected subject instead of form tabs."""
    data = payload.model_dump()
    subject = db.get(Subject, payload.subject_id)
    if not subject:
        raise NotFoundError("Subject not found")
    course = db.get(Course, subject.course_id) if subject.course_id else None
    data["branch_id"] = course.branch_id if course else None
    data["semester_id"] = subject.semester_id
    semester = db.get(Semester, subject.semester_id) if subject.semester_id else None
    data["academic_year_id"] = semester.academic_year_id if semester else None
    return data


@router.post("/schedules")
def create_schedule(payload: ScheduleCreate, admin: ExamAdmin, db: DbSession) -> dict:
    if payload.end_time <= payload.start_time:
        raise ValidationError("End time must be after start time")
    exam = db.get(Examination, payload.examination_id)
    if not exam:
        raise NotFoundError("Examination not found")
    data = _schedule_scope(db, payload)
    conflict = (
        db.query(ExaminationSchedule)
        .filter(
            ExaminationSchedule.exam_date == data["exam_date"],
            ExaminationSchedule.branch_id == data["branch_id"],
            ExaminationSchedule.semester_id == data["semester_id"],
            or_(
                ExaminationSchedule.start_time < payload.end_time,
                ExaminationSchedule.end_time > payload.start_time,
            ),
        )
        .first()
    )
    if conflict:
        raise ConflictError("A schedule already exists for this group at the overlapping time")
    schedule = ExaminationSchedule(**data)
    db.add(schedule)
    log_action(db, user=admin, action="SCHEDULE_CREATED", entity_type="ExaminationSchedule", entity_id=str(schedule.id), new=data)
    db.commit()
    return ok({"id": schedule.id}, "Schedule created")


@router.patch("/schedules/{schedule_id}")
def update_schedule(schedule_id: UUID, payload: ScheduleCreate, admin: ExamAdmin, db: DbSession) -> dict:
    schedule = get_or_404(db, ExaminationSchedule, schedule_id)
    if payload.end_time <= payload.start_time:
        raise ValidationError("End time must be after start time")
    previous = {
        "exam_date": str(schedule.exam_date), "start_time": str(schedule.start_time),
        "end_time": str(schedule.end_time), "venue": schedule.venue,
    }
    for field, value in _schedule_scope(db, payload).items():
        setattr(schedule, field, value)
    schedule.change_count += 1
    log_action(db, user=admin, action="SCHEDULE_UPDATED", entity_type="ExaminationSchedule", entity_id=str(schedule_id), previous=previous)
    db.commit()
    return ok(message="Schedule updated")


@router.get("/timetables")
def timetables(admin: ExamAdmin, db: DbSession) -> dict:
    rows = db.query(ExaminationSchedule).order_by(ExaminationSchedule.exam_date).all()
    return ok([
        {
            "id": s.id, "examination_name": s.examination.name,
            "subject_code": s.subject.subject_code, "subject_name": s.subject.subject_name,
            "exam_date": s.exam_date.isoformat(), "start_time": s.start_time.strftime("%H:%M"),
            "end_time": s.end_time.strftime("%H:%M"), "session": s.session, "venue": s.venue,
            "publication_status": s.publication_status, "change_count": s.change_count,
        }
        for s in rows
    ], "Timetable")


@router.post("/timetables/publish")
def publish_timetable(admin: ExamAdmin, db: DbSession, examination_id: UUID | None = None) -> dict:
    query = db.query(ExaminationSchedule)
    if examination_id:
        query = query.filter(ExaminationSchedule.examination_id == examination_id)
    rows = query.all()
    if not rows:
        raise ValidationError("No schedule entries exist to publish")
    for row in rows:
        row.publication_status = PublicationStatus.PUBLISHED
    log_action(db, user=admin, action="TIMETABLE_PUBLISHED", entity_type="ExaminationSchedule", entity_id=str(examination_id or "all"), new={"count": len(rows)})
    db.commit()
    return ok({"published": len(rows)}, "Timetable published")


@router.get("/timetables/download")
def download_timetable(admin: ExamAdmin, db: DbSession) -> Response:
    rows = db.query(ExaminationSchedule).order_by(ExaminationSchedule.exam_date).all()
    pdf = render_timetable({
        "title": "EXAMINATION TIMETABLE (ADMIN COPY)",
        "rows": [
            {
                "date": s.exam_date.isoformat(), "start_time": s.start_time.strftime("%H:%M"),
                "end_time": s.end_time.strftime("%H:%M"), "session": s.session,
                "code": s.subject.subject_code, "name": s.subject.subject_name, "venue": s.venue,
            }
            for s in rows
        ],
    })
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="timetable-admin.pdf"'})


@router.post("/hall-tickets/generate")
def generate_hall_tickets(admin: ExamAdmin, db: DbSession, examination_id: UUID) -> dict:
    exam = db.get(Examination, examination_id)
    if not exam:
        raise NotFoundError("Examination not found")
    registrations = (
        db.query(ExaminationRegistration)
        .filter_by(examination_id=examination_id, status=RegistrationStatus.SUBMITTED)
        .all()
    )
    generated = 0
    for registration in registrations:
        existing = db.query(HallTicket).filter_by(
            student_id=registration.student_id, examination_id=examination_id
        ).first()
        if existing:
            continue
        ticket = HallTicket(
            student_id=registration.student_id,
            examination_id=examination_id,
            ticket_number=f"HT-{exam.exam_type[:3]}-{str(uuid4()).upper()[:10]}",
            generated_by=admin.id,
            issued_at=datetime.now(timezone.utc),
        )
        db.add(ticket)
        generated += 1
    log_action(db, user=admin, action="HALL_TICKETS_GENERATED", entity_type="HallTicket", entity_id=str(examination_id), new={"count": generated})
    db.commit()
    return ok({"generated": generated, "registrations": len(registrations)}, "Hall tickets generated")


@router.get("/hall-tickets")
def list_hall_tickets(admin: ExamAdmin, db: DbSession, examination_id: UUID | None = None) -> dict:
    query = db.query(HallTicket)
    if examination_id:
        query = query.filter(HallTicket.examination_id == examination_id)
    rows = query.all()
    return ok([
        {
            "id": t.id, "ticket_number": t.ticket_number, "student_id": t.student_id,
            "student_name": t.student.full_name, "roll_number": t.student.roll_number,
            "examination_id": t.examination_id, "examination_name": t.examination.name,
            "issued_at": t.issued_at, "is_valid": t.is_valid,
        }
        for t in rows
    ], "Hall tickets")


@router.post("/hall-tickets/{ticket_id}/regenerate")
def regenerate_hall_ticket(ticket_id: UUID, admin: ExamAdmin, db: DbSession) -> dict:
    ticket = get_or_404(db, HallTicket, ticket_id)
    ticket.ticket_number = f"HT-R-{str(uuid4()).upper()[:10]}"
    ticket.issued_at = datetime.now(timezone.utc)
    ticket.is_valid = True
    log_action(db, user=admin, action="HALL_TICKET_REGENERATED", entity_type="HallTicket", entity_id=str(ticket_id))
    db.commit()
    return ok({"ticket_number": ticket.ticket_number}, "Hall ticket regenerated")
