"""Examination Admin: marks verification, result processing, publication and operations."""
from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from io import BytesIO, StringIO
from secrets import token_urlsafe
from uuid import UUID

from fastapi import APIRouter, File, Form, Response, UploadFile
from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import CurrentUser, DbSession, ExamAdmin, get_or_404
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.core.responses import as_number, ok
from app.models.academic import Course, Regulation, Semester, Subject
from app.models.enums import (
    CorrectionStatus,
    NotificationCategory,
    PublicationStatus,
    RecountingStatus,
    RegistrationStatus,
    ResultStatus,
    Role,
    SubmissionStatus,
)
from app.models.examination import Examination, ExaminationRegistration, ExaminationSubject
from app.models.marks import InternalMark, MarksSubmission, StudentMarkCorrectionRequest
from app.models.misc import PasswordResetToken
from app.models.notification import AuditLog
from app.models.result import (
    Backlog,
    ExternalMark,
    ExternalMarkImport,
    RecountingRequest,
    RecountingRequestHistory,
    SemesterResult,
    SubjectResult,
)
from app.models.user import Faculty, Student, User
from app.schemas.auth import AdminInitiateResetRequest
from app.schemas.result import PublicationIn, RecountingProcess, ResultProcessIn
from app.services.academic_scope import subject_belongs_to_student
from app.services.audit import log_action
from app.services.grading import GradeConfig, calculate_cgpa, calculate_sgpa, percentage_of
from app.services.notifications import notify_users

router = APIRouter()


# ---------------------------------------------------------------------------
# Marks verification and management
# ---------------------------------------------------------------------------
def _mark_row(mark: InternalMark) -> dict:
    return {
        "id": mark.id,
        "student_id": mark.student_id,
        "student_name": mark.student.full_name,
        "roll_number": mark.student.roll_number,
        "subject_id": mark.subject_id,
        "subject_code": mark.subject.subject_code,
        "subject_name": mark.subject.subject_name,
        "faculty_id": mark.faculty_id,
        "component_marks": mark.component_marks,
        "mid1_marks": as_number(mark.mid1_marks),
        "mid2_marks": as_number(mark.mid2_marks),
        "assignments_marks": as_number(mark.assignments_marks),
        "total_marks": as_number(mark.total_marks),
        "max_marks": mark.max_marks,
        "status": mark.status,
    }


@router.get("/internal-marks")
def internal_marks(admin: ExamAdmin, db: DbSession, subject_id: UUID | None = None, status: SubmissionStatus | None = None) -> dict:
    query = db.query(InternalMark)
    if subject_id:
        query = query.filter(InternalMark.subject_id == subject_id)
    if status:
        query = query.filter(InternalMark.status == status)
    return ok([_mark_row(m) for m in query.order_by(InternalMark.subject_id, InternalMark.student_id).all()], "Internal marks")


@router.get("/marks-verification")
def marks_verification(admin: ExamAdmin, db: DbSession) -> dict:
    rows = db.query(MarksSubmission).order_by(MarksSubmission.created_at.desc()).all()
    return ok([
        {
            "id": r.id, "faculty_id": r.faculty_id, "subject_id": r.subject_id,
            "subject_code": r.subject.subject_code, "subject_name": r.subject.subject_name,
            "status": r.status, "submitted_at": r.submitted_at, "review_note": r.review_note,
            "mark_count": db.query(InternalMark).filter_by(
                subject_id=r.subject_id, examination_id=r.examination_id
            ).count(),
        }
        for r in rows
    ], "Marks submissions awaiting verification")


@router.post("/marks-verification/{submission_id}")
def review_submission(
    submission_id: UUID, action: str, admin: ExamAdmin, user: CurrentUser, db: DbSession, note: str | None = None
) -> dict:
    if action not in {"approve", "return", "lock"}:
        raise ValidationError("action must be approve, return or lock")
    submission = get_or_404(db, MarksSubmission, submission_id)
    if action == "lock" and submission.status not in (SubmissionStatus.VERIFIED, SubmissionStatus.SUBMITTED):
        raise ConflictError("Only submitted or verified marks can be locked")
    if action == "approve":
        submission.status = SubmissionStatus.VERIFIED
    elif action == "return":
        submission.status = SubmissionStatus.RETURNED
    else:
        submission.status = SubmissionStatus.LOCKED
    submission.reviewed_by = admin.id
    submission.reviewed_at = datetime.now(timezone.utc)
    submission.review_note = note
    marks = db.query(InternalMark).filter_by(
        subject_id=submission.subject_id, examination_id=submission.examination_id
    ).all()
    for mark in marks:
        mark.status = submission.status
        if submission.status == SubmissionStatus.VERIFIED:
            mark.verified_at = submission.reviewed_at
            mark.verified_by = admin.id
        if submission.status == SubmissionStatus.LOCKED:
            mark.locked_at = submission.reviewed_at
    log_action(db, user=user, action=f"MARKS_{action.upper()}", entity_type="MarksSubmission", entity_id=str(submission_id), new={"status": submission.status})
    faculty = db.get(Faculty, submission.faculty_id)
    if faculty:
        notify_users(
            db, sender=user, user_ids=[faculty.user_id], title=f"Marks submission {submission.status.lower()}",
            message=f"Your marks submission for {submission.subject.subject_code} is now {submission.status}.",
            category=NotificationCategory.MARKS_SUBMISSION,
        )
    db.commit()
    return ok({"status": submission.status}, "Marks submission updated")


@router.get("/marks-management")
def marks_management(admin: ExamAdmin, db: DbSession, student_id: UUID | None = None, subject_id: UUID | None = None) -> dict:
    from app.models.academic import AcademicYear

    year_names = {y.id: y.academic_year_name for y in db.query(AcademicYear).all()}
    exams = {e.id: e for e in db.query(Examination).all()}
    exam_years = {eid: e.academic_year_id for eid, e in exams.items()}
    internal_query = db.query(InternalMark)
    external_query = db.query(ExternalMark)
    if student_id:
        internal_query = internal_query.filter(InternalMark.student_id == student_id)
        external_query = external_query.filter(ExternalMark.student_id == student_id)
    if subject_id:
        internal_query = internal_query.filter(InternalMark.subject_id == subject_id)
        external_query = external_query.filter(ExternalMark.subject_id == subject_id)
    return ok({
        "internal": [_mark_row(m) for m in internal_query.all()],
        "external": [
            {
                "id": m.id, "student_id": m.student_id,
                "student_name": m.student.full_name, "roll_number": m.student.roll_number,
                "subject_id": m.subject_id, "subject_code": m.subject.subject_code,
                "subject_name": m.subject.subject_name,
                "examination_id": m.examination_id,
                "examination_name": exams[m.examination_id].name if m.examination_id in exams else None,
                "semester_id": m.subject.semester_id,
                "academic_year_name": year_names.get(exam_years.get(m.examination_id)),
                "marks_obtained": as_number(m.marks_obtained), "max_marks": m.max_marks,
                "entered_at": m.created_at,
            }
            for m in external_query.all()
        ],
    }, "Marks management")


@router.post("/marks-management/external")
def enter_external_marks(payload: list[dict], admin: ExamAdmin, user: CurrentUser, db: DbSession) -> dict:
    """Bulk external marks entry. Each item: student_id, subject_id, examination_id, marks_obtained."""
    saved = 0
    for item in payload:
        student = db.get(Student, item.get("student_id"))
        subject = db.get(Subject, item.get("subject_id"))
        exam = db.get(Examination, item.get("examination_id"))
        if not student or not subject or not exam:
            raise ValidationError("Student, subject or examination not found")
        if not subject_belongs_to_student(db, subject, student):
            raise ValidationError("Subject is outside the student's current semester or branch")
        try:
            marks = float(item.get("marks_obtained"))
        except (TypeError, ValueError):
            raise ValidationError("External marks must be a valid number")
        if marks < 0 or marks > subject.external_max_marks:
            raise ValidationError(f"External marks must be between 0 and {subject.external_max_marks}")
        record = (
            db.query(ExternalMark)
            .filter_by(student_id=student.id, subject_id=subject.id, examination_id=exam.id)
            .first()
        )
        previous = record.marks_obtained if record else None
        if not record:
            record = ExternalMark(
                student_id=student.id, subject_id=subject.id, examination_id=exam.id,
                max_marks=subject.external_max_marks, entered_by=admin.id,
            )
            db.add(record)
        record.marks_obtained = marks
        record.max_marks = subject.external_max_marks
        log_action(db, user=user, action="EXTERNAL_MARKS_ENTERED", entity_type="ExternalMark", entity_id=str(record.id), previous=previous, new={"marks": marks})
        saved += 1
    db.commit()
    return ok({"saved": saved}, "External marks saved")


# ---------------------------------------------------------------------------
# Result processing
# ---------------------------------------------------------------------------
def _regulation_for_subject(db: Session, subject: Subject) -> Regulation | None:
    if subject.course_id:
        course = db.get(Course, subject.course_id)
        if course and course.regulation_id:
            return db.get(Regulation, course.regulation_id)
    if subject.semester_id:
        semester = db.get(Semester, subject.semester_id)
        if semester and semester.regulation_id:
            return db.get(Regulation, semester.regulation_id)
    return None


@router.post("/result-processing")
def process_results(payload: ResultProcessIn, admin: ExamAdmin, user: CurrentUser, db: DbSession) -> dict:
    exam = db.get(Examination, payload.examination_id)
    if not exam:
        raise NotFoundError("Examination not found")
    exam_subjects = db.query(ExaminationSubject).filter_by(examination_id=exam.id, is_eligible=True).all()
    if not exam_subjects:
        raise ValidationError("Examination has no eligible subjects")
    subject_ids = [es.subject_id for es in exam_subjects]
    subjects = db.query(Subject).filter(Subject.id.in_(subject_ids)).all()
    # Grade and pass rules are centralized in app.services.grading; no JSON
    # regulation configuration is required or consulted here.
    config = GradeConfig()
    exam_subject_map = {s.id: s for s in subjects}
    registrations_query = db.query(ExaminationRegistration).filter(
        ExaminationRegistration.examination_id == exam.id,
        ExaminationRegistration.status.in_([RegistrationStatus.SUBMITTED, RegistrationStatus.CONFIRMED]),
    )
    if payload.student_ids:
        registrations_query = registrations_query.filter(ExaminationRegistration.student_id.in_(payload.student_ids))
    registrations = registrations_query.all()
    processed: list[UUID] = []
    errors: list[dict] = []
    for registration in registrations:
        student = registration.student
        registered_subject_ids = [
            rs.subject_id for rs in registration.subjects
            if not (es := exam_subject_map.get(rs.subject_id))
            or subject_belongs_to_student(db, es, student)
        ]
        if not registered_subject_ids:
            errors.append({"student": student.roll_number, "issues": ["no subjects for the student's current semester and branch"]})
            continue
        subject_results: list[SubjectResult] = []
        missing: list[str] = []
        for subject_id in registered_subject_ids:
            subject = exam_subject_map.get(subject_id)
            if not subject:
                continue
            internal = (
                db.query(InternalMark)
                .filter_by(student_id=student.id, subject_id=subject_id, examination_id=exam.id)
                .first()
            )
            external = (
                db.query(ExternalMark)
                .filter_by(student_id=student.id, subject_id=subject_id, examination_id=exam.id)
                .first()
            )
            if not internal or internal.status not in (SubmissionStatus.VERIFIED, SubmissionStatus.LOCKED):
                missing.append(f"{subject.subject_code}: internal marks missing or not verified")
                continue
            if not external:
                missing.append(f"{subject.subject_code}: external marks missing")
                continue
            total = internal.total_marks + external.marks_obtained
            maximum = subject.internal_max_marks + subject.external_max_marks
            percentage = (total / maximum * 100) if maximum else 0
            grade, grade_point, _ = config.grade_for(percentage)
            passed = config.is_pass(
                internal.total_marks, subject.internal_max_marks,
                external.marks_obtained, subject.external_max_marks, total, maximum,
            )
            subject_results.append(SubjectResult(
                subject_id=subject_id,
                internal_marks=internal.total_marks,
                external_marks=external.marks_obtained,
                total_marks=total,
                max_marks=maximum,
                credits=subject.credits,
                grade=grade,
                grade_point=grade_point,
                result_status=ResultStatus.PASS if passed else ResultStatus.BACKLOG,
            ))
        if missing:
            errors.append({"student": student.roll_number, "issues": missing})
            continue
        semester = subjects[0].semester_id
        sem_number = student.current_semester
        academic_year = student.academic_year
        if semester:
            sem_obj = db.get(Semester, semester)
            if sem_obj:
                sem_number = sem_obj.semester_number
        existing = (
            db.query(SemesterResult)
            .filter_by(student_id=student.id, examination_id=exam.id)
            .first()
        )
        previous = (
            db.query(SemesterResult)
            .filter(SemesterResult.student_id == student.id, SemesterResult.status == PublicationStatus.PUBLISHED)
            .all()
        )
        sgpa, credits, earned = calculate_sgpa(subject_results, config)
        cgpa = calculate_cgpa(previous, sgpa, credits, config)
        result = existing or SemesterResult(
            student_id=student.id, examination_id=exam.id,
            semester_id=semester, academic_year_id=exam.academic_year_id,
        )
        if existing:
            # Re-processing must replace the subject rows, not append a second
            # set with the same (semester_result_id, subject_id) pair. Expire
            # the collection afterwards so the deleted rows are not cascaded
            # back into the session by db.add(result).
            db.query(SubjectResult).filter_by(semester_result_id=existing.id).delete(
                synchronize_session=False
            )
            db.expire(existing, ["subject_results"])
        result.semester_number = sem_number
        result.academic_year_name = academic_year
        result.sgpa = sgpa
        result.cgpa = cgpa
        result.total_credits = credits
        result.earned_credits = earned
        result.status = PublicationStatus.READY_FOR_REVIEW
        result.subject_results = subject_results
        db.add(result)
        db.flush()
        for sr in result.subject_results:
            if sr.result_status == ResultStatus.BACKLOG:
                backlog = db.query(Backlog).filter_by(student_id=student.id, subject_id=sr.subject_id).first()
                if not backlog:
                    backlog = Backlog(
                        student_id=student.id, subject_id=sr.subject_id,
                        semester_number=sem_number, academic_year_name=academic_year, attempts=1,
                    )
                    db.add(backlog)
                elif not backlog.is_cleared:
                    backlog.attempts += 1
            else:
                backlog = db.query(Backlog).filter_by(student_id=student.id, subject_id=sr.subject_id).first()
                if backlog and not backlog.is_cleared:
                    backlog.is_cleared = True
                    backlog.cleared_at = datetime.now(timezone.utc)
                    backlog.cleared_by_result_id = result.id
        processed.append(result.id)
        log_action(db, user=user, action="RESULT_PROCESSED", entity_type="SemesterResult", entity_id=str(result.id), new={"sgpa": sgpa, "cgpa": cgpa})
    if not processed and errors:
        db.rollback()
        raise ValidationError("No results could be processed", errors=errors)
    exam.status = "PROCESSING"
    db.commit()
    return ok({"processed": len(processed), "result_ids": [str(x) for x in processed], "errors": errors}, "Results processed (not yet published)")


@router.get("/results")
def list_results(admin: ExamAdmin, db: DbSession, status: PublicationStatus | None = None) -> dict:
    query = db.query(SemesterResult)
    if status:
        query = query.filter(SemesterResult.status == status)
    rows = query.order_by(SemesterResult.semester_number, SemesterResult.student_id).all()
    return ok([
        {
            "id": r.id, "student_id": r.student_id, "student_name": r.student.full_name,
            "roll_number": r.student.roll_number, "semester_number": r.semester_number,
            "academic_year_name": r.academic_year_name, "sgpa": float(r.sgpa) if r.sgpa is not None else None,
            "cgpa": float(r.cgpa) if r.cgpa is not None else None, "status": r.status,
            "subject_count": len(r.subject_results), "published_at": r.published_at,
        }
        for r in rows
    ], "Semester results")


@router.post("/result-publication/{result_id}")
def publication_action(
    result_id: UUID, payload: PublicationIn, admin: ExamAdmin, user: CurrentUser, db: DbSession
) -> dict:
    result = get_or_404(db, SemesterResult, result_id)
    if payload.action == "approve":
        if result.status not in (PublicationStatus.READY_FOR_REVIEW, PublicationStatus.APPROVED):
            raise ConflictError("Only results ready for review can be approved")
        result.status = PublicationStatus.APPROVED
        result.approved_by = admin.id
    elif payload.action == "publish":
        if result.status != PublicationStatus.APPROVED:
            raise ConflictError("Result must be approved before publication")
        if not result.subject_results:
            raise ValidationError("Cannot publish a result without subject results")
        result.status = PublicationStatus.PUBLISHED
        result.published_at = datetime.now(timezone.utc)
        notify_users(
            db, sender=user, user_ids=[result.student.user_id], title="Semester result published",
            message=f"Your Semester {result.semester_number} result has been published.",
            category=NotificationCategory.RESULT,
        )
    elif payload.action == "unpublish":
        if result.status != PublicationStatus.PUBLISHED:
            raise ConflictError("Result is not published")
        result.status = PublicationStatus.APPROVED
        result.published_at = None
    log_action(db, user=user, action=f"RESULT_{payload.action.upper()}", entity_type="SemesterResult", entity_id=str(result_id), new={"status": result.status, "note": payload.note})
    db.commit()
    return ok({"status": result.status}, f"Result {payload.action} completed")


@router.get("/sgpa-cgpa")
def sgpa_cgpa(admin: ExamAdmin, db: DbSession) -> dict:
    rows = db.query(SemesterResult).order_by(SemesterResult.student_id, SemesterResult.semester_number).all()
    regulations = db.query(Regulation).all()
    return ok({
        "results": [
            {
                "id": r.id, "student_id": r.student_id, "roll_number": r.student.roll_number,
                "semester": r.semester_number, "sgpa": float(r.sgpa) if r.sgpa is not None else None,
                "cgpa": float(r.cgpa) if r.cgpa is not None else None, "status": r.status,
            }
            for r in rows
        ],
        "regulations": [
            {
                "id": reg.id, "regulation_name": reg.regulation_name,
                "grade_rules": reg.grade_rules, "pass_rules": reg.pass_rules,
                "calculation_rules": reg.calculation_rules,
            }
            for reg in regulations
        ],
    }, "SGPA / CGPA overview and configured rules")


# ---------------------------------------------------------------------------
# Backlogs and recounting
# ---------------------------------------------------------------------------
@router.get("/backlogs")
def backlogs(admin: ExamAdmin, db: DbSession) -> dict:
    rows = db.query(Backlog).order_by(Backlog.student_id, Backlog.semester_number).all()
    return ok([
        {
            "id": b.id, "student_id": b.student_id, "student_name": b.student.full_name,
            "roll_number": b.student.roll_number, "subject_id": b.subject_id,
            "subject_code": b.subject.subject_code, "subject_name": b.subject.subject_name,
            "credits": b.subject.credits, "semester_number": b.semester_number,
            "academic_year_name": b.academic_year_name, "attempts": b.attempts,
            "is_cleared": b.is_cleared, "supplementary_exam_id": b.supplementary_exam_id,
        }
        for b in rows
    ], "Backlogs")


@router.patch("/backlogs/{backlog_id}")
def update_backlog(backlog_id: UUID, supplementary_exam_id: UUID | None, admin: ExamAdmin, db: DbSession) -> dict:
    backlog = get_or_404(db, Backlog, backlog_id)
    if supplementary_exam_id and not db.get(Examination, supplementary_exam_id):
        raise NotFoundError("Examination not found")
    backlog.supplementary_exam_id = supplementary_exam_id
    log_action(db, user=admin, action="BACKLOG_SUPPLEMENTARY_SET", entity_type="Backlog", entity_id=str(backlog_id))
    db.commit()
    return ok(message="Backlog updated")


@router.get("/recounting")
def recounting_requests(admin: ExamAdmin, db: DbSession, status: RecountingStatus | None = None) -> dict:
    query = db.query(RecountingRequest)
    if status:
        query = query.filter(RecountingRequest.request_status == status)
    rows = query.order_by(RecountingRequest.created_at.desc()).all()
    return ok([
        {
            "id": r.id, "student_id": r.student_id, "student_name": r.student.full_name,
            "roll_number": r.student.roll_number, "examination_id": r.examination_id,
            "examination_name": r.examination.name, "subject_id": r.subject_id,
            "subject_code": r.subject.subject_code, "subject_name": r.subject.subject_name,
            "original_marks": as_number(r.original_marks), "reason": r.reason,
            "request_status": r.request_status, "admin_response": r.admin_response,
            "revised_marks": as_number(r.revised_marks, default=None), "created_at": r.created_at,
        }
        for r in rows
    ], "Recounting requests")


@router.post("/recounting/{request_id}/process")
def process_recounting(
    request_id: UUID, payload: RecountingProcess, admin: ExamAdmin, user: CurrentUser, db: DbSession
) -> dict:
    request = get_or_404(db, RecountingRequest, request_id)
    if request.request_status in (RecountingStatus.COMPLETED, RecountingStatus.REJECTED):
        raise ConflictError("This request is already closed")
    mapping = {
        "pending_review": RecountingStatus.PENDING_REVIEW,
        "processing": RecountingStatus.PROCESSING,
        "complete": RecountingStatus.COMPLETED,
        "reject": RecountingStatus.REJECTED,
    }
    new_status = mapping[payload.action]
    previous = request.request_status
    request.request_status = new_status
    request.admin_response = payload.admin_response
    request.processed_by = admin.id
    if payload.revised_marks is not None:
        subject = get_or_404(db, Subject, request.subject_id)
        maximum = subject.internal_max_marks + subject.external_max_marks
        if payload.revised_marks < 0 or payload.revised_marks > maximum:
            raise ValidationError(f"Revised marks must be between 0 and {maximum} for {subject.subject_code}")
        request.revised_marks = payload.revised_marks
    if new_status in (RecountingStatus.COMPLETED, RecountingStatus.REJECTED):
        request.completed_at = datetime.now(timezone.utc)
    if new_status == RecountingStatus.COMPLETED and payload.revised_marks is not None:
        result = (
            db.query(SemesterResult)
            .filter_by(student_id=request.student_id, examination_id=request.examination_id)
            .first()
        )
        if result:
            sr = next((s for s in result.subject_results if s.subject_id == request.subject_id), None)
            if sr:
                old_total = sr.total_marks
                old_grade = sr.grade
                external_marks = payload.revised_marks - float(sr.internal_marks)
                if external_marks < 0 or external_marks > subject.external_max_marks:
                    raise ValidationError(
                        f"Revised total implies external marks outside 0-{subject.external_max_marks}"
                    )
                sr.external_marks = external_marks
                sr.total_marks = payload.revised_marks
                grading = GradeConfig()
                grade, grade_point, _ = grading.grade_for(percentage_of(sr.total_marks, sr.max_marks))
                sr.grade = grade
                sr.grade_point = grade_point
                sr.result_status = (
                    ResultStatus.PASS
                    if grading.is_pass(sr.internal_marks, sr.max_marks, sr.external_marks, sr.max_marks, sr.total_marks, sr.max_marks)
                    else ResultStatus.BACKLOG
                )
                previous_results = (
                    db.query(SemesterResult)
                    .filter(
                        SemesterResult.student_id == request.student_id,
                        SemesterResult.status == PublicationStatus.PUBLISHED,
                        SemesterResult.id != result.id,
                    )
                    .all()
                )
                result.sgpa, credits, earned = calculate_sgpa(result.subject_results, grading)
                result.total_credits = credits
                result.earned_credits = earned
                result.cgpa = calculate_cgpa(previous_results, result.sgpa, credits, grading)
                result.status = PublicationStatus.READY_FOR_REVIEW
                log_action(
                    db, user=user, action="RESULT_REVISED_BY_RECOUNTING", entity_type="SubjectResult",
                    entity_id=str(sr.id), previous={"total": old_total, "grade": old_grade},
                    new={"total": payload.revised_marks, "grade": grade},
                )
                backlog = db.query(Backlog).filter_by(
                    student_id=request.student_id, subject_id=request.subject_id
                ).first()
                if sr.result_status == ResultStatus.BACKLOG and not backlog:
                    db.add(Backlog(
                        student_id=request.student_id, subject_id=request.subject_id,
                        semester_number=result.semester_number,
                        academic_year_name=result.academic_year_name, attempts=1,
                    ))
                elif sr.result_status == ResultStatus.PASS and backlog and not backlog.is_cleared:
                    backlog.is_cleared = True
                    backlog.cleared_at = datetime.now(timezone.utc)
                    backlog.cleared_by_result_id = result.id
    db.add(RecountingRequestHistory(
        request_id=request.id, from_status=previous, to_status=new_status,
        note=payload.admin_response, changed_by=admin.id,
    ))
    log_action(db, user=user, action="RECOUNTING_PROCESSED", entity_type="RecountingRequest", entity_id=str(request_id), new={"status": new_status})
    notify_users(
        db, sender=user, user_ids=[request.student.user_id], title="Recounting request updated",
        message=f"Your recounting request for {request.subject.subject_code} is now {new_status}.",
        category=NotificationCategory.RECOUNTING,
    )
    db.commit()
    return ok({"status": new_status}, "Recounting request updated")


# ---------------------------------------------------------------------------
# Admin view of student correction requests
# ---------------------------------------------------------------------------
@router.get("/mark-correction-requests")
def admin_correction_requests(admin: ExamAdmin, db: DbSession) -> dict:
    rows = (
        db.query(StudentMarkCorrectionRequest)
        .order_by(StudentMarkCorrectionRequest.created_at.desc())
        .all()
    )
    return ok([
        {
            "id": r.id,
            "student_id": r.student_id,
            "student_name": r.student.full_name,
            "roll_number": r.student.roll_number,
            "subject_id": r.subject_id,
            "subject_code": r.subject_code or r.subject.subject_code,
            "reported_marks": as_number(r.reported_marks_value),
            "suggested_marks": as_number(r.suggested_marks_value),
            "explanation": r.explanation,
            "request_status": r.request_status,
            "faculty_response": r.faculty_response,
            "created_at": r.created_at,
        }
        for r in rows
    ], "Marks correction requests")


# ---------------------------------------------------------------------------
# External marks CSV import (validate -> preview -> explicit confirm)
# ---------------------------------------------------------------------------
CSV_REQUIRED_COLUMNS = {"rollno", "subcode", "marks"}
# ``ext`` was the old column name. It is still accepted so an import staged
# before the rename can be confirmed and older templates keep working.
CSV_COLUMN_ALIASES = {"ext": "marks"}
CSV_MAX_BYTES = 5 * 1024 * 1024
CSV_MAX_ROWS = 10_000


@router.get("/result-processing/sample-csv")
def sample_csv(admin: ExamAdmin, db: DbSession) -> Response:
    students = db.query(Student).order_by(Student.roll_number).limit(3).all()
    subjects = db.query(Subject).order_by(Subject.subject_code).limit(1).all()
    maximum = subjects[0].external_max_marks if subjects else 70
    lines = ["rollno,subcode,marks"]
    if students and subjects:
        for student in students:
            lines.append(f"{student.roll_number},{subjects[0].subject_code},52")
    else:
        lines.append(f"21A01A0501,CS301,{maximum}")
    return Response("\n".join(lines) + "\n", media_type="text/csv", headers={
        "Content-Disposition": 'attachment; filename="external-marks-sample.csv"'
    })


def _parse_csv(content: bytes) -> list[dict]:
    if len(content) > CSV_MAX_BYTES:
        raise ValidationError("CSV file must be 5 MB or smaller")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValidationError("CSV file must be UTF-8 encoded")
    reader = csv.DictReader(StringIO(text))
    headers = {
        CSV_COLUMN_ALIASES.get((h or "").strip().lower(), (h or "").strip().lower())
        for h in (reader.fieldnames or [])
    }
    missing = CSV_REQUIRED_COLUMNS - headers
    if missing:
        raise ValidationError(f"CSV is missing required column(s): {', '.join(sorted(missing))}")
    rows = [
        {
            CSV_COLUMN_ALIASES.get((key or "").strip().lower(), (key or "").strip().lower()): value
            for key, value in row.items()
        }
        for row in reader
    ]
    if not rows:
        raise ValidationError("CSV file contains no data rows")
    if len(rows) > CSV_MAX_ROWS:
        raise ValidationError(f"CSV file may contain at most {CSV_MAX_ROWS} rows")
    return rows


@router.post("/result-processing/import")
async def preview_external_marks_import(
    admin: ExamAdmin,
    user: CurrentUser,
    db: DbSession,
    examination_id: UUID = Form(...),
    file: UploadFile = File(...),
) -> dict:
    """Parse and validate a CSV without writing any marks."""
    if not (file.filename or "").lower().endswith(".csv"):
        raise ValidationError("Please upload a .csv file")
    exam = db.get(Examination, examination_id)
    if not exam:
        raise NotFoundError("Examination not found")
    content = await file.read(CSV_MAX_BYTES + 1)
    raw_rows = _parse_csv(content)
    students = {s.roll_number.strip().upper(): s for s in db.query(Student).all()}
    subjects = {s.subject_code.strip().upper(): s for s in db.query(Subject).all()}
    seen: set[tuple[str, str]] = set()
    rows: list[dict] = []
    summary = {"total": len(raw_rows), "valid": 0, "invalid": 0, "skipped": 0}
    for index, raw in enumerate(raw_rows, start=2):
        rollno = (raw.get("rollno") or "").strip().upper()
        subcode = (raw.get("subcode") or "").strip().upper()
        marks_raw = (raw.get("marks") or "").strip()
        errors: list[str] = []
        if not rollno:
            errors.append("rollno is empty")
        if not subcode:
            errors.append("subcode is empty")
        student = students.get(rollno)
        subject = subjects.get(subcode)
        if rollno and not student:
            errors.append(f"roll number '{rollno}' does not exist")
        if subcode and not subject:
            errors.append(f"subject code '{subcode}' does not exist")
        if student and subject and not subject_belongs_to_student(db, subject, student):
            errors.append("subject is outside the student's current semester or branch")
        try:
            marks = float(marks_raw)
            if marks != marks or marks in (float("inf"), float("-inf")):
                raise ValueError
        except (TypeError, ValueError):
            marks = None
            errors.append("marks must be a number")
        if subject and marks is not None and (marks < 0 or marks > subject.external_max_marks):
            errors.append(f"marks must be between 0 and {subject.external_max_marks}")
        key = (rollno, subcode)
        if key in seen:
            errors.append("duplicate rollno/subcode in this file")
        seen.add(key)
        existing = None
        if student and subject:
            existing = (
                db.query(ExternalMark)
                .filter_by(student_id=student.id, subject_id=subject.id, examination_id=exam.id)
                .first()
            )
        status = "invalid" if errors else ("skipped" if existing else "valid")
        if status == "invalid":
            summary["invalid"] += 1
        elif status == "skipped":
            summary["skipped"] += 1
        else:
            summary["valid"] += 1
        rows.append({
            "row": index,
            "rollno": rollno,
            "subcode": subcode,
            "marks": marks,
            "student_id": str(student.id) if student else None,
            "subject_id": str(subject.id) if subject else None,
            "student_name": student.full_name if student else None,
            "subject_name": subject.subject_name if subject else None,
            "max_marks": subject.external_max_marks if subject else None,
            "status": status,
            "errors": errors,
            "existing_marks": float(existing.marks_obtained) if existing else None,
        })
    staging = ExternalMarkImport(
        admin_id=user.id, examination_id=exam.id, filename=file.filename or "external-marks.csv",
        rows=rows, summary=summary, status="PENDING",
    )
    db.add(staging)
    db.commit()
    log_action(
        db, user=user, action="EXTERNAL_MARKS_CSV_VALIDATED", entity_type="ExternalMarkImport",
        entity_id=str(staging.id), new={"filename": staging.filename, **summary}, commit=True,
    )
    return ok({
        "import_id": staging.id,
        "examination_id": exam.id,
        "examination_name": exam.name,
        "filename": staging.filename,
        "rows": rows,
        "summary": summary,
    }, "CSV validated — review the preview before confirming")


@router.post("/result-processing/import/{import_id}/confirm")
def confirm_external_marks_import(
    import_id: UUID,
    admin: ExamAdmin,
    user: CurrentUser,
    db: DbSession,
    overwrite: bool = False,
) -> dict:
    staging = db.get(ExternalMarkImport, import_id)
    if not staging or staging.admin_id != user.id:
        raise NotFoundError("Import record not found")
    if staging.status != "PENDING":
        raise ConflictError("This import has already been processed")
    exam = db.get(Examination, staging.examination_id)
    if not exam:
        raise NotFoundError("Examination not found")
    applied = 0
    skipped = 0
    failed: list[dict] = []
    for row in staging.rows:
        if row.get("status") not in ({"valid", "skipped"} if overwrite else {"valid"}):
            continue
        try:
            student = db.get(Student, UUID(row["student_id"]))
            subject = db.get(Subject, UUID(row["subject_id"]))
            if not student or not subject:
                raise ValueError("Student or subject no longer exists")
            if not subject_belongs_to_student(db, subject, student):
                raise ValueError("Subject is outside the student's current semester or branch")
            marks = float(row["marks"])
            if marks < 0 or marks > subject.external_max_marks:
                raise ValueError("Marks outside permitted range")
        except (KeyError, TypeError, ValueError) as exc:
            failed.append({"row": row.get("row"), "errors": [str(exc)]})
            continue
        record = (
            db.query(ExternalMark)
            .filter_by(student_id=student.id, subject_id=subject.id, examination_id=exam.id)
            .first()
        )
        if record and not overwrite:
            skipped += 1
            continue
        if not record:
            record = ExternalMark(
                student_id=student.id, subject_id=subject.id, examination_id=exam.id,
                entered_by=user.id,
            )
            db.add(record)
        record.marks_obtained = marks
        record.max_marks = subject.external_max_marks
        applied += 1
    staging.status = "CONFIRMED"
    staging.imported_at = datetime.now(timezone.utc)
    staging.summary = {
        **staging.summary,
        "applied": applied,
        "skipped": skipped,
        "failed": len(failed),
        "overwrite": overwrite,
    }
    log_action(
        db, user=user, action="EXTERNAL_MARKS_IMPORTED", entity_type="ExternalMarkImport",
        entity_id=str(staging.id), new=staging.summary,
    )
    db.commit()
    return ok({
        "import_id": staging.id,
        "applied": applied,
        "skipped": skipped,
        "failed": failed,
        "summary": staging.summary,
    }, "External marks imported. Results are not published automatically.")


# ---------------------------------------------------------------------------
# Reports, password reset and audit
# ---------------------------------------------------------------------------
REPORT_QUERIES = {
    "students": lambda db: [
        {"roll_number": s.roll_number, "name": s.full_name, "email": s.user.email,
         "branch": s.branch.branch_code if s.branch else "", "semester": s.current_semester}
        for s in db.query(Student).all()
    ],
    "faculty": lambda db: [
        {"faculty_id": f.faculty_id, "name": f.full_name, "email": f.user.email,
         "designation": f.designation, "status": f.account_status}
        for f in db.query(Faculty).all()
    ],
    "registrations": lambda db: [
        {"student": r.student.roll_number, "examination": r.examination.name,
         "status": r.status, "subjects": len(r.subjects)}
        for r in db.query(ExaminationRegistration).all()
    ],
    "results": lambda db: [
        {"student": r.student.roll_number, "semester": r.semester_number,
         "sgpa": r.sgpa, "cgpa": r.cgpa, "status": r.status}
        for r in db.query(SemesterResult).all()
    ],
    "backlogs": lambda db: [
        {"student": b.student.roll_number, "subject": b.subject.subject_code,
         "semester": b.semester_number, "attempts": b.attempts, "cleared": b.is_cleared}
        for b in db.query(Backlog).all()
    ],
    "recounting": lambda db: [
        {"student": r.student.roll_number, "subject": r.subject.subject_code,
         "original": r.original_marks, "status": r.request_status}
        for r in db.query(RecountingRequest).all()
    ],
}


@router.get("/reports/{report_type}")
def export_report(report_type: str, admin: ExamAdmin, db: DbSession, format: str = "csv") -> Response:
    builder = REPORT_QUERIES.get(report_type)
    if not builder:
        raise NotFoundError(f"Unknown report type '{report_type}'")
    rows = builder(db)
    columns = list(rows[0].keys()) if rows else ["no_data"]
    if format == "xlsx":
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(columns)
        for row in rows:
            sheet.append([str(row.get(c, "")) for c in columns])
        buffer = BytesIO()
        workbook.save(buffer)
        return Response(
            buffer.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{report_type}.xlsx"'},
        )
    if format != "csv":
        raise ValidationError("format must be csv or xlsx")
    import csv

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    for row in rows:
        writer.writerow({c: row.get(c, "") for c in columns})
    return Response(
        output.getvalue().encode("utf-8"), media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{report_type}.csv"'},
    )


@router.post("/password-reset/initiate")
def initiate_password_reset(
    payload: AdminInitiateResetRequest, admin: ExamAdmin, user: CurrentUser, db: DbSession
) -> dict:
    target = db.get(User, payload.user_id)
    if not target or target.role not in (Role.STUDENT, Role.FACULTY):
        raise NotFoundError("Student or faculty account not found")
    token = token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    db.add(PasswordResetToken(
        user_id=target.id, token_hash=sha256(token.encode()).hexdigest(),
        expires_at=expires, requested_by=admin.id,
    ))
    log_action(db, user=user, action="PASSWORD_RESET_INITIATED", entity_type="User", entity_id=str(target.id), new={"reason": payload.reason})
    db.commit()
    response = {
        "reset_token": token if settings.environment != "production" else None,
        "expires_at": expires.isoformat(),
        "user_id": target.id,
        "note": "Deliver this token to the user through a secure channel. In production, send via configured email/SMS provider.",
    }
    return ok(response, "Password reset initiated")


@router.get("/audit-logs")
def audit_logs(admin: ExamAdmin, db: DbSession, page: int = 1, page_size: int = 20) -> dict:
    page = max(1, page)
    page_size = max(1, min(200, page_size))
    total = db.query(AuditLog).count()
    rows = db.query(AuditLog).order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return ok({
        "items": [
            {
                "id": r.id, "user_id": r.user_id, "user_role": r.user_role, "action": r.action,
                "entity_type": r.entity_type, "entity_id": r.entity_id, "created_at": r.created_at,
            }
            for r in rows
        ],
        "total": total, "page": page, "page_size": page_size,
        "pages": max(1, (total + page_size - 1) // page_size),
    }, "Audit log")
