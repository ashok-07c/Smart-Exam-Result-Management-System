"""Student portal endpoints. All academic decisions are made here, never in the client."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core.deps import CurrentStudent, CurrentUser, DbSession, get_pagination
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.core.responses import as_number, ok, Page
from app.models.academic import FacultyAssignment, Semester, Subject
from app.models.enums import (
    CorrectionStatus,
    ExamType,
    NotificationCategory,
    PublicationStatus,
    RecountingStatus,
    RegistrationStatus,
    Role,
)
from app.models.examination import (
    Examination,
    ExaminationEligibility,
    ExaminationRegistration,
    ExaminationSchedule,
    RegistrationSubject,
)
from app.models.marks import InternalMark, StudentMarkCorrectionRequest
from app.models.misc import HallTicket
from app.models.notification import Notification, NotificationRecipient
from app.models.result import Backlog, RecountingRequest, RecountingRequestHistory, SemesterResult
from app.models.user import Faculty, Student, User
from app.schemas.examination import RegistrationCreate
from app.schemas.marks import CorrectionCreate
from app.schemas.result import RecountingCreate
from app.schemas.user import StudentSelfUpdate
from app.services.academic_scope import subject_belongs_to_student
from app.services.audit import log_action
from app.services.notifications import notify_users
from app.utils.pdf import render_certificate, render_hall_ticket, render_timetable
from app.utils.uploads import delete_receipt, receipt_path, save_receipt, validate_receipt

router = APIRouter()


def _student_out(student: Student) -> dict:
    return {
        "id": student.id,
        "user_id": student.user_id,
        "roll_number": student.roll_number,
        "full_name": student.full_name,
        "email": student.user.email,
        "department": student.department.department_name if student.department else None,
        "branch": student.branch.branch_name if student.branch else None,
        "department_id": student.department_id,
        "branch_id": student.branch_id,
        "current_semester": student.current_semester,
        "academic_year": student.academic_year,
        "admission_year": student.admission_year,
        "enrollment_status": student.enrollment_status,
        "section": student.section,
    }


def _registration_out(reg: ExaminationRegistration) -> dict:
    return {
        "id": reg.id,
        "examination_id": reg.examination_id,
        "examination_name": reg.examination.name,
        "exam_type": reg.examination.exam_type,
        "student_id": reg.student_id,
        "status": reg.status,
        "submitted_at": reg.submitted_at,
        "fee_receipt_filename": reg.fee_receipt_filename,
        "fee_receipt_uploaded_at": reg.fee_receipt_uploaded_at,
        "has_fee_receipt": bool(reg.fee_receipt_path),
        "subjects": [
            {
                "subject_id": rs.subject_id,
                "subject_code": rs.subject.subject_code,
                "subject_name": rs.subject.subject_name,
                "credits": rs.subject.credits,
            }
            for rs in reg.subjects
        ],
    }


def exam_is_eligible(db: Session, exam: Examination, student: Student) -> tuple[bool, str]:
    now = datetime.now(timezone.utc)
    start = exam.registration_start
    deadline = exam.registration_deadline
    if start and start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if deadline and deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    if exam.status != "OPEN":
        return False, "Examination registration is not open"
    if start and now < start:
        return False, "Examination registration has not started"
    if deadline and now > deadline:
        return False, "Examination registration deadline has passed"
    criteria = exam.eligibility_criteria or {}
    # Announcements are common to all branches; branch filtering is applied only
    # to subjects, never to the exam itself.
    if criteria.get("eligible_semesters") and student.current_semester not in criteria["eligible_semesters"]:
        return False, "Your semester is not eligible"
    if criteria.get("min_semester") and student.current_semester < criteria["min_semester"]:
        return False, "Your semester is below the minimum requirement"
    if criteria.get("max_backlogs") is not None:
        active = db.query(Backlog).filter(Backlog.student_id == student.id, Backlog.is_cleared.is_(False)).count()
        if active > criteria["max_backlogs"]:
            return False, "You have too many active backlogs"
    override = db.query(ExaminationEligibility).filter_by(examination_id=exam.id, student_id=student.id).first()
    if override and not override.is_eligible:
        return False, override.reason or "You are not eligible for this examination"
    return True, "Eligible"


def eligible_subjects(db: Session, exam: Examination, student: Student) -> list[Subject]:
    exam_subject_ids = [es.subject_id for es in exam.subjects if es.is_eligible]
    if not exam_subject_ids:
        return []
    subjects = db.query(Subject).filter(Subject.id.in_(exam_subject_ids)).all()
    subjects = [s for s in subjects if subject_belongs_to_student(db, s, student)]
    criteria = exam.eligibility_criteria or {}
    if exam.exam_type == ExamType.SUPPLEMENTARY and criteria.get("require_backlog", True):
        backlog_subject_ids = {
            b.subject_id for b in db.query(Backlog).filter_by(student_id=student.id, is_cleared=False)
        }
        subjects = [s for s in subjects if s.id in backlog_subject_ids]
    return subjects


@router.get("/me")
def get_me(student: CurrentStudent) -> dict:
    return ok(_student_out(student), "Student profile")


@router.patch("/me/profile")
def update_profile(payload: StudentSelfUpdate, student: CurrentStudent, user: CurrentUser, db: DbSession) -> dict:
    """Students may edit personal details only; eligibility context is admin-owned."""
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(student, field, value)
    if payload.full_name:
        user.full_name = payload.full_name
    log_action(
        db, user=user, action="STUDENT_PROFILE_UPDATED", entity_type="Student",
        entity_id=str(student.id), new=updates, commit=True,
    )
    return ok(_student_out(student), "Profile updated")


@router.get("/me/examinations")
def list_eligible_examinations(student: CurrentStudent, db: DbSession) -> dict:
    exams = db.query(Examination).order_by(Examination.registration_deadline).all()
    result = []
    for exam in exams:
        eligible, reason = exam_is_eligible(db, exam, student)
        registered = db.query(ExaminationRegistration).filter_by(examination_id=exam.id, student_id=student.id).first()
        result.append({
            "id": exam.id,
            "name": exam.name,
            "exam_type": exam.exam_type,
            "registration_start": exam.registration_start,
            "registration_deadline": exam.registration_deadline,
            "eligible": eligible,
            "eligibility_reason": reason,
            "registered": registered is not None,
            "registration_id": registered.id if registered else None,
            "subject_count": len(eligible_subjects(db, exam, student)),
        })
    return ok(result, "Eligible examinations")


@router.get("/me/examinations/{examination_id}/subjects")
def eligible_subjects_for_exam(examination_id: UUID, student: CurrentStudent, db: DbSession) -> dict:
    exam = db.get(Examination, examination_id)
    if not exam:
        raise NotFoundError("Examination not found")
    eligible, reason = exam_is_eligible(db, exam, student)
    if not eligible:
        raise ForbiddenError(reason)
    subjects = eligible_subjects(db, exam, student)
    registered = db.query(ExaminationRegistration).filter_by(examination_id=exam.id, student_id=student.id).first()
    already = {rs.subject_id for rs in registered.subjects} if registered else set()
    return ok([
        {
            "subject_id": s.id,
            "subject_code": s.subject_code,
            "subject_name": s.subject_name,
            "credits": s.credits,
            "internal_max_marks": s.internal_max_marks,
            "external_max_marks": s.external_max_marks,
            "already_registered": s.id in already,
        }
        for s in subjects
    ], "Eligible subjects")


@router.post("/me/registrations")
def register(
    student: CurrentStudent,
    user: CurrentUser,
    db: DbSession,
    examination_id: UUID = Form(...),
    subject_ids: list[UUID] = Form(...),
    fee_receipt: UploadFile = File(...),
) -> dict:
    """Register with a mandatory SBI Collect fee receipt (multipart/form-data)."""
    validate_receipt(fee_receipt)
    exam = db.get(Examination, examination_id)
    if not exam:
        raise NotFoundError("Examination not found")
    eligible, reason = exam_is_eligible(db, exam, student)
    if not eligible:
        raise ForbiddenError(reason)
    existing = db.query(ExaminationRegistration).filter_by(
        examination_id=exam.id, student_id=student.id
    ).first()
    if existing and existing.status != RegistrationStatus.CANCELLED:
        raise ConflictError("You are already registered for this examination")
    allowed = {s.id for s in eligible_subjects(db, exam, student)}
    requested = set(subject_ids)
    if not requested or not requested.issubset(allowed):
        raise ValidationError("One or more selected subjects are not eligible for this examination")
    relative_path, original_name, content_type = save_receipt(
        fee_receipt, student_id=student.id, examination_id=exam.id
    )
    previous_path = existing.fee_receipt_path if existing else None
    try:
        registration = existing or ExaminationRegistration(
            examination_id=exam.id, student_id=student.id, status=RegistrationStatus.SUBMITTED
        )
        registration.status = RegistrationStatus.SUBMITTED
        registration.submitted_at = datetime.now(timezone.utc)
        registration.fee_receipt_path = relative_path
        registration.fee_receipt_filename = original_name
        registration.fee_receipt_content_type = content_type
        registration.fee_receipt_uploaded_at = datetime.now(timezone.utc)
        db.add(registration)
        db.flush()
        if existing:
            db.query(RegistrationSubject).filter_by(registration_id=registration.id).delete()
            db.flush()
        for subject_id in requested:
            db.add(RegistrationSubject(registration_id=registration.id, subject_id=subject_id))
        log_action(
            db, user=user, action="EXAM_REGISTRATION_SUBMITTED", entity_type="ExaminationRegistration",
            entity_id=str(registration.id),
            new={"examination_id": str(exam.id), "subject_ids": [str(x) for x in requested], "fee_receipt": original_name},
        )
        log_action(
            db, user=user, action="EXAM_REGISTRATION_CONFIRMED", entity_type="ExaminationRegistration",
            entity_id=str(registration.id),
        )
        db.commit()
        db.refresh(registration)
    except Exception:
        db.rollback()
        delete_receipt(relative_path)
        raise
    if previous_path and previous_path != relative_path:
        delete_receipt(previous_path)
    return ok(_registration_out(registration), "Registration submitted successfully")


@router.get("/me/registrations/{registration_id}/receipt")
def download_own_receipt(registration_id: UUID, student: CurrentStudent, db: DbSession) -> FileResponse:
    registration = db.get(ExaminationRegistration, registration_id)
    if not registration or registration.student_id != student.id or not registration.fee_receipt_path:
        raise NotFoundError("Fee receipt not found")
    path = receipt_path(registration.fee_receipt_path)
    media_type = registration.fee_receipt_content_type or "application/pdf"
    return FileResponse(path, media_type=media_type, filename=registration.fee_receipt_filename or "fee-receipt")


@router.get("/me/registrations")
def registration_history(student: CurrentStudent, db: DbSession) -> dict:
    regs = (
        db.query(ExaminationRegistration)
        .filter(ExaminationRegistration.student_id == student.id)
        .order_by(ExaminationRegistration.created_at.desc())
        .all()
    )
    return ok([_registration_out(r) for r in regs], "Registration history")


def _visible_timetable(
    db: Session,
    student: Student,
    exam_type: ExamType | None = None,
    subject_code: str | None = None,
) -> list[ExaminationSchedule]:
    """Published schedules limited to this student's semester and own branch."""
    query = (
        db.query(ExaminationSchedule)
        .join(Examination, ExaminationSchedule.examination_id == Examination.id)
        .filter(ExaminationSchedule.publication_status == PublicationStatus.PUBLISHED)
    )
    if exam_type:
        query = query.filter(Examination.exam_type == exam_type)
    rows = []
    for schedule in query.order_by(ExaminationSchedule.exam_date, ExaminationSchedule.start_time).all():
        if not subject_belongs_to_student(db, schedule.subject, student):
            continue
        if subject_code and subject_code.lower() not in schedule.subject.subject_code.lower():
            continue
        rows.append(schedule)
    return rows


@router.get("/me/timetable")
def timetable(
    student: CurrentStudent,
    db: DbSession,
    exam_type: ExamType | None = None,
    subject_code: str | None = None,
) -> dict:
    return ok([_schedule_out(s) for s in _visible_timetable(db, student, exam_type, subject_code)], "Published timetable")


def _schedule_out(schedule: ExaminationSchedule) -> dict:
    return {
        "id": schedule.id,
        "examination_id": schedule.examination_id,
        "examination_name": schedule.examination.name,
        "exam_type": schedule.examination.exam_type,
        "subject_id": schedule.subject_id,
        "subject_code": schedule.subject.subject_code,
        "subject_name": schedule.subject.subject_name,
        "exam_date": schedule.exam_date.isoformat(),
        "start_time": schedule.start_time.strftime("%H:%M"),
        "end_time": schedule.end_time.strftime("%H:%M"),
        "session": schedule.session,
        "venue": schedule.venue,
        "publication_status": schedule.publication_status,
    }


@router.get("/me/timetable/download")
def download_timetable(student: CurrentStudent, db: DbSession) -> Response:
    rows = [_schedule_out(s) for s in _visible_timetable(db, student)]
    pdf = render_timetable({
        "title": "PUBLISHED EXAMINATION TIMETABLE",
        "rows": [
            {
                "date": r["exam_date"], "start_time": r["start_time"], "end_time": r["end_time"],
                "session": r["session"], "code": r["subject_code"], "name": r["subject_name"],
                "venue": r["venue"],
            }
            for r in rows
        ],
    })
    return Response(
        pdf, media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="timetable.pdf"'},
    )


@router.get("/me/hall-tickets")
def hall_tickets(student: CurrentStudent, db: DbSession) -> dict:
    tickets = (
        db.query(HallTicket)
        .filter(HallTicket.student_id == student.id, HallTicket.is_valid.is_(True))
        .order_by(HallTicket.created_at.desc())
        .all()
    )
    return ok([
        {
            "id": t.id,
            "ticket_number": t.ticket_number,
            "examination_id": t.examination_id,
            "examination_name": t.examination.name,
            "exam_type": t.examination.exam_type,
            "issued_at": t.issued_at,
            "is_valid": t.is_valid,
        }
        for t in tickets
    ], "Hall tickets")


def _hall_ticket_payload(db: Session, ticket, student: Student) -> dict:
    regs = db.query(ExaminationRegistration).filter_by(
        student_id=student.id, examination_id=ticket.examination_id
    ).first()
    schedules = {
        s.subject_id: s
        for s in db.query(ExaminationSchedule).filter_by(examination_id=ticket.examination_id).all()
    }
    exam = db.get(Examination, ticket.examination_id)
    allowed = {s.id for s in eligible_subjects(db, exam, student)} if exam else set()
    items = []
    for rs in regs.subjects if regs else []:
        if rs.subject_id not in allowed:
            continue
        schedule = schedules.get(rs.subject_id)
        items.append({
            "code": rs.subject.subject_code,
            "name": rs.subject.subject_name,
            "date": schedule.exam_date.isoformat() if schedule else "-",
            "start_time": schedule.start_time.strftime("%H:%M") if schedule else "-",
            "end_time": schedule.end_time.strftime("%H:%M") if schedule else "-",
            "session": schedule.session if schedule else "-",
            "venue": schedule.venue if schedule else "-",
        })
    return {
        "student_name": student.full_name,
        "roll_number": student.roll_number,
        "branch": student.branch.branch_name if student.branch else "-",
        "semester": student.current_semester,
        "academic_year": student.academic_year,
        "examination": ticket.examination.name,
        "ticket_number": ticket.ticket_number,
        "issue_date": (ticket.issued_at or ticket.created_at).date().isoformat(),
        "subjects": items,
    }


@router.get("/me/hall-tickets/{ticket_id}")
def preview_hall_ticket(ticket_id: UUID, student: CurrentStudent, db: DbSession) -> dict:
    ticket = db.get(HallTicket, ticket_id)
    if not ticket or ticket.student_id != student.id:
        raise NotFoundError("Hall ticket not found")
    return ok(_hall_ticket_payload(db, ticket, student), "Hall ticket preview")


@router.get("/me/hall-tickets/{ticket_id}/download")
def download_hall_ticket(ticket_id: UUID, student: CurrentStudent, db: DbSession) -> Response:
    ticket = db.get(HallTicket, ticket_id)
    if not ticket or ticket.student_id != student.id or not ticket.is_valid:
        raise NotFoundError("Hall ticket not found")
    pdf = render_hall_ticket(_hall_ticket_payload(db, ticket, student))
    return Response(
        pdf, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="hall-ticket-{student.roll_number}.pdf"'},
    )


@router.get("/me/internal-marks")
def internal_marks(student: CurrentStudent, db: DbSession) -> dict:
    marks = (
        db.query(InternalMark)
        .filter(InternalMark.student_id == student.id)
        .order_by(InternalMark.created_at.desc())
        .all()
    )
    return ok([
        {
            "id": m.id,
            "student_id": m.student_id,
            "subject_id": m.subject_id,
            "subject_code": m.subject.subject_code,
            "subject_name": m.subject.subject_name,
            "component_marks": m.component_marks,
            "mid1_marks": as_number(m.mid1_marks),
            "mid2_marks": as_number(m.mid2_marks),
            "assignments_marks": as_number(m.assignments_marks),
            "total_marks": as_number(m.total_marks),
            "max_marks": m.max_marks,
            "status": m.status,
            "submitted_at": m.submitted_at,
        }
        for m in marks
    ], "Internal marks")


@router.post("/me/mark-correction-requests")
def create_correction(payload: CorrectionCreate, student: CurrentStudent, user: CurrentUser, db: DbSession) -> dict:
    code = payload.subject_code.strip().upper()
    mark = (
        db.query(InternalMark)
        .join(Subject, InternalMark.subject_id == Subject.id)
        .filter(InternalMark.student_id == student.id, Subject.subject_code == code)
        .first()
    )
    if not mark:
        raise NotFoundError(f"No internal mark record found for subject {code}")
    subject = mark.subject
    maximum = subject.internal_max_marks + subject.external_max_marks
    for label, value in (("Reported marks", payload.reported_marks), ("Suggested marks", payload.suggested_marks)):
        if value > maximum:
            raise ValidationError(f"{label} cannot exceed {maximum} for {code}")
    faculty_assignment = db.query(FacultyAssignment).filter_by(
        subject_id=subject.id, assignment_status="ACTIVE"
    ).first()
    faculty_record = None
    if faculty_assignment:
        faculty_record = db.get(Faculty, faculty_assignment.faculty_id)
    request = StudentMarkCorrectionRequest(
        student_id=student.id,
        subject_id=subject.id,
        faculty_id=faculty_record.id if faculty_record else None,
        subject_code=code,
        reported_marks={"value": payload.reported_marks, "subject_code": code},
        suggested_marks={"value": payload.suggested_marks, "subject_code": code},
        reported_marks_value=payload.reported_marks,
        suggested_marks_value=payload.suggested_marks,
        explanation=payload.explanation,
        request_status=CorrectionStatus.SUBMITTED,
    )
    db.add(request)
    db.flush()
    log_action(db, user=user, action="MARK_CORRECTION_REPORTED", entity_type="StudentMarkCorrectionRequest", entity_id=str(request.id))
    if faculty_record:
        notify_users(
            db, sender=user, user_ids=[faculty_record.user_id], title="Internal marks error reported",
            message=f"{student.full_name} reported a marks discrepancy in {code}.",
            category=NotificationCategory.MARKS_CORRECTION,
        )
    db.commit()
    return ok({"id": request.id}, "Marks error report submitted")


@router.get("/me/mark-correction-requests")
def correction_requests(student: CurrentStudent, db: DbSession) -> dict:
    requests = (
        db.query(StudentMarkCorrectionRequest)
        .filter_by(student_id=student.id)
        .order_by(StudentMarkCorrectionRequest.created_at.desc())
        .all()
    )
    return ok([
        {
            "id": r.id,
            "student_id": r.student_id,
            "subject_id": r.subject_id,
            "subject_code": r.subject_code or r.subject.subject_code,
            "subject_name": r.subject.subject_name,
            "reported_marks": as_number(r.reported_marks_value),
            "suggested_marks": as_number(r.suggested_marks_value),
            "explanation": r.explanation,
            "request_status": r.request_status,
            "faculty_response": r.faculty_response,
            "created_at": r.created_at,
        }
        for r in requests
    ], "Correction requests")


def _result_out(db: Session, result: SemesterResult, student: Student) -> dict:
    return {
        "id": result.id,
        "student_id": result.student_id,
        "examination_id": result.examination_id,
        "examination_name": result.examination.name if result.examination else None,
        "semester_number": result.semester_number,
        "academic_year_name": result.academic_year_name,
        "sgpa": float(result.sgpa) if result.sgpa is not None else None,
        "cgpa": float(result.cgpa) if result.cgpa is not None else None,
        "total_credits": result.total_credits,
        "earned_credits": result.earned_credits,
        "status": result.status,
        "published_at": result.published_at,
        "subject_results": [
            {
                "id": sr.id,
                "subject_id": sr.subject_id,
                "subject_code": sr.subject.subject_code,
                "subject_name": sr.subject.subject_name,
                "credits": sr.credits,
                "internal_marks": as_number(sr.internal_marks),
                "external_marks": as_number(sr.external_marks),
                "total_marks": as_number(sr.total_marks),
                "max_marks": sr.max_marks,
                "grade": sr.grade,
                "grade_point": float(sr.grade_point),
                "result_status": sr.result_status,
            }
            for sr in result.subject_results
            if subject_belongs_to_student(db, sr.subject, student)
        ],
    }


@router.get("/me/results")
def results(student: CurrentStudent, db: DbSession, academic_year: str | None = None) -> dict:
    query = db.query(SemesterResult).filter(
        SemesterResult.student_id == student.id,
        SemesterResult.status == PublicationStatus.PUBLISHED,
    )
    if academic_year:
        query = query.filter(SemesterResult.academic_year_name == academic_year)
    rows = query.order_by(SemesterResult.semester_number).all()
    return ok([_result_out(db, r, student) for r in rows], "Published results")


@router.get("/me/results/{result_id}")
def result_detail(result_id: UUID, student: CurrentStudent, db: DbSession) -> dict:
    result = db.get(SemesterResult, result_id)
    if not result or result.student_id != student.id or result.status != PublicationStatus.PUBLISHED:
        raise NotFoundError("Published result not found")
    return ok(_result_out(db, result, student), "Result detail")


@router.get("/me/sgpa-cgpa")
def performance(student: CurrentStudent, db: DbSession) -> dict:
    rows = (
        db.query(SemesterResult)
        .filter(SemesterResult.student_id == student.id, SemesterResult.status == PublicationStatus.PUBLISHED)
        .order_by(SemesterResult.semester_number)
        .all()
    )
    semesters = [
        {
            "semester": r.semester_number,
            "academic_year": r.academic_year_name,
            "sgpa": float(r.sgpa) if r.sgpa is not None else None,
            "cgpa": float(r.cgpa) if r.cgpa is not None else None,
            "status": r.status,
        }
        for r in rows
    ]
    return ok({"semesters": semesters, "current_cgpa": semesters[-1]["cgpa"] if semesters else None}, "Academic performance")


@router.get("/me/certificates/{result_id}/download")
def download_certificate(result_id: UUID, student: CurrentStudent, user: CurrentUser, db: DbSession) -> Response:
    result = db.get(SemesterResult, result_id)
    if not result or result.student_id != student.id:
        raise NotFoundError("Result not found")
    if result.status != PublicationStatus.PUBLISHED:
        raise ForbiddenError("Certificate is available only for published results")
    if not result.certificate_reference:
        from uuid import uuid4

        result.certificate_reference = f"CERT-{str(uuid4()).upper()[:12]}"
        db.commit()
    payload = {
        "student_name": student.full_name,
        "roll_number": student.roll_number,
        "branch": student.branch.branch_name if student.branch else "-",
        "semester": result.semester_number,
        "academic_year": result.academic_year_name,
        "examination": "Regular / Supplementary",
        "sgpa": result.sgpa,
        "cgpa": result.cgpa,
        "issue_date": date.today().isoformat(),
        "verification_reference": result.certificate_reference,
        "subjects": [
            {
                "code": sr.subject.subject_code,
                "name": sr.subject.subject_name,
                "credits": sr.credits,
                "marks": f"{sr.total_marks}/{sr.max_marks}",
                "grade": sr.grade,
                "status": sr.result_status,
            }
            for sr in result.subject_results
            if subject_belongs_to_student(db, sr.subject, student)
        ],
    }
    pdf = render_certificate(payload)
    log_action(db, user=user, action="CERTIFICATE_DOWNLOADED", entity_type="SemesterResult", entity_id=str(result.id), commit=True)
    return Response(
        pdf, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="certificate-sem-{result.semester_number}.pdf"'},
    )


@router.get("/me/backlogs")
def backlogs(student: CurrentStudent, db: DbSession) -> dict:
    rows = (
        db.query(Backlog)
        .filter(Backlog.student_id == student.id)
        .order_by(Backlog.semester_number)
        .all()
    )
    return ok([
        {
            "id": b.id,
            "subject_id": b.subject_id,
            "subject_code": b.subject.subject_code,
            "subject_name": b.subject.subject_name,
            "credits": b.subject.credits,
            "semester_number": b.semester_number,
            "academic_year_name": b.academic_year_name,
            "attempts": b.attempts,
            "is_cleared": b.is_cleared,
            "supplementary_exam_id": b.supplementary_exam_id,
        }
        for b in rows
    ], "Backlogs")


@router.post("/me/recounting-requests")
def create_recounting(payload: RecountingCreate, student: CurrentStudent, user: CurrentUser, db: DbSession) -> dict:
    exam = db.get(Examination, payload.examination_id)
    if not exam:
        raise NotFoundError("Examination not found")
    now = datetime.now(timezone.utc)
    published_query = db.query(SemesterResult).filter_by(
        student_id=student.id, examination_id=exam.id, status=PublicationStatus.PUBLISHED
    )
    if payload.result_id:
        published_query = published_query.filter(SemesterResult.id == payload.result_id)
    published = published_query.order_by(SemesterResult.published_at.desc()).first()
    if not published:
        raise ForbiddenError("A published result for this examination is required before requesting recounting")
    recounting_until = (exam.eligibility_criteria or {}).get("recounting_until")
    if recounting_until:
        try:
            cutoff = datetime.fromisoformat(str(recounting_until).replace("Z", "+00:00"))
            if cutoff.tzinfo is None:
                cutoff = cutoff.replace(tzinfo=timezone.utc)
        except ValueError:
            raise ValidationError("Invalid recounting window configuration")
    else:
        # A 30-day window from publication is the safe default; the registration
        # deadline must not be used because results are published after it.
        basis = published.published_at or published.created_at
        if basis and basis.tzinfo is None:
            basis = basis.replace(tzinfo=timezone.utc)
        cutoff = (basis + timedelta(days=30)) if basis else now
    if now > cutoff:
        raise ForbiddenError("The recounting request window has closed")
    subject_result = next((sr for sr in published.subject_results if sr.subject_id == payload.subject_id), None)
    if not subject_result:
        raise ForbiddenError("This subject is not part of your published result")
    existing = db.query(RecountingRequest).filter_by(
        student_id=student.id, examination_id=exam.id, subject_id=payload.subject_id
    ).first()
    if existing:
        raise ConflictError("You have already submitted a recounting request for this subject")
    request = RecountingRequest(
        student_id=student.id,
        examination_id=exam.id,
        subject_id=payload.subject_id,
        original_marks=subject_result.total_marks,
        reason=payload.reason,
        request_status=RecountingStatus.SUBMITTED,
    )
    db.add(request)
    db.flush()
    db.add(RecountingRequestHistory(
        request_id=request.id, from_status=None, to_status=RecountingStatus.SUBMITTED,
        note=payload.reason, changed_by=user.id,
    ))
    log_action(db, user=user, action="RECOUNTING_REQUESTED", entity_type="RecountingRequest", entity_id=str(request.id))
    admins = db.query(User).filter_by(role=Role.EXAM_ADMIN).all()
    notify_users(
        db, sender=user, user_ids=[a.id for a in admins], title="New recounting request",
        message=f"{student.full_name} requested recounting for {subject_result.subject.subject_code}.",
        category=NotificationCategory.RECOUNTING,
    )
    db.commit()
    return ok({"id": request.id}, "Recounting request submitted")


@router.get("/me/recounting-requests")
def recounting_requests(student: CurrentStudent, db: DbSession) -> dict:
    rows = (
        db.query(RecountingRequest)
        .filter_by(student_id=student.id)
        .order_by(RecountingRequest.created_at.desc())
        .all()
    )
    return ok([
        {
            "id": r.id,
            "student_id": r.student_id,
            "examination_id": r.examination_id,
            "examination_name": r.examination.name,
            "subject_id": r.subject_id,
            "subject_code": r.subject.subject_code,
            "subject_name": r.subject.subject_name,
            "original_marks": as_number(r.original_marks),
            "reason": r.reason,
            "request_status": r.request_status,
            "admin_response": r.admin_response,
            "revised_marks": as_number(r.revised_marks, default=None),
            "created_at": r.created_at,
            "completed_at": r.completed_at,
        }
        for r in rows
    ], "Recounting requests")


@router.get("/me/notifications")
def student_notifications(
    student: CurrentStudent, db: DbSession, category: NotificationCategory | None = None,
    unread_only: bool = False, page: int = 1, page_size: int = 20,
) -> dict:
    page, page_size = get_pagination(page, page_size)
    query = (
        db.query(NotificationRecipient)
        .join(Notification, NotificationRecipient.notification_id == Notification.id)
        .filter(NotificationRecipient.recipient_user_id == student.user_id)
    )
    if category:
        query = query.filter(Notification.category == category)
    if unread_only:
        query = query.filter(NotificationRecipient.read_at.is_(None))
    total = query.count()
    rows = query.order_by(Notification.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = [
        {
            "id": r.id,
            "notification_id": r.notification_id,
            "title": r.notification.title,
            "message": r.notification.message,
            "category": r.notification.category,
            "sender_id": r.notification.sender_id,
            "created_at": r.notification.created_at,
            "published_at": r.notification.published_at,
            "read": r.read_at is not None,
            "read_at": r.read_at,
        }
        for r in rows
    ]
    return ok(Page.build(items, total, page, page_size).model_dump(mode="json"), "Notifications")

