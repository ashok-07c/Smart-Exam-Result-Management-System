"""Faculty portal endpoints. Every subject/class access is verified against assignments."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core.deps import CurrentFaculty, CurrentUser, DbSession, get_pagination
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.core.responses import as_number, ok, Page
from app.models.academic import FacultyAssignment, Semester, Subject
from app.models.enums import (
    CorrectionStatus,
    NotificationCategory,
    PublicationStatus,
    SubmissionStatus,
)
from app.models.examination import Examination, ExaminationSchedule, ExaminationSubject
from app.models.marks import (
    InternalMark,
    InternalMarkComponent,
    MarksSubmission,
    StudentMarkCorrectionRequest,
)
from app.models.notification import Notification, NotificationRecipient
from app.models.user import Faculty, Student, User
from app.schemas.marks import BulkMarksIn, CorrectionReview
from app.services.academic_scope import resolve_subject_scope
from app.services.audit import log_action
from app.services.internal_marks import (
    INTERNAL_COMPONENTS,
    calculate_internal_total,
    component_marks,
    validate_components,
)
from app.services.notifications import notify_users

router = APIRouter()


def assert_assigned(db: Session, faculty_id: UUID, subject_id: UUID) -> FacultyAssignment:
    assignment = (
        db.query(FacultyAssignment)
        .filter(
            FacultyAssignment.faculty_id == faculty_id,
            FacultyAssignment.subject_id == subject_id,
            FacultyAssignment.assignment_status == "ACTIVE",
        )
        .first()
    )
    if not assignment:
        raise ForbiddenError("You are not assigned to this subject")
    return assignment


def _infer_examination_id(db: Session, subject_id: UUID) -> UUID | None:
    """Return the single open/eligible examination containing a subject, if any."""
    exam_ids = {
        link.examination_id
        for link in db.query(ExaminationSubject).filter(
            ExaminationSubject.subject_id == subject_id,
            ExaminationSubject.is_eligible.is_(True),
        ).all()
    }
    return exam_ids.pop() if len(exam_ids) == 1 else None


def _resolve_examination_id(db: Session, subject_id: UUID, supplied: UUID | None) -> UUID:
    """Bind internal marks to an examination so result processing can find them."""
    if supplied:
        exam = db.get(Examination, supplied)
        if not exam:
            raise NotFoundError("Examination not found")
        link = db.query(ExaminationSubject).filter_by(
            examination_id=exam.id, subject_id=subject_id, is_eligible=True
        ).first()
        if not link:
            raise ValidationError("This subject is not part of the selected examination")
        return exam.id
    exam_id = _infer_examination_id(db, subject_id)
    if not exam_id:
        raise ValidationError("No eligible examination is configured for this subject")
    return exam_id


def _assignment_scope(db: Session, assignment: FacultyAssignment) -> tuple[UUID | None, UUID | None, int | None]:
    """Resolve assignment scope from the subject's academic chain, failing closed."""
    subject = db.get(Subject, assignment.subject_id)
    if not subject:
        raise NotFoundError("Subject not found")
    department_id, branch_id, semester_number = resolve_subject_scope(db, subject)
    if not semester_number and assignment.semester_id:
        semester = db.get(Semester, assignment.semester_id)
        semester_number = semester.semester_number if semester else None
    department_id = department_id or None
    branch_id = branch_id or assignment.branch_id
    if not any((department_id, branch_id, semester_number)):
        # Never fall back to "all students" when the academic chain is broken.
        raise ForbiddenError("Your assignment has no resolvable academic scope")
    return department_id, branch_id, semester_number


def faculty_profile(faculty: Faculty, db: Session) -> dict:
    assignments = (
        db.query(FacultyAssignment)
        .filter(FacultyAssignment.faculty_id == faculty.id, FacultyAssignment.assignment_status == "ACTIVE")
        .all()
    )
    return {
        "id": faculty.id,
        "user_id": faculty.user_id,
        "faculty_id": faculty.faculty_id,
        "full_name": faculty.full_name,
        "email": faculty.user.email,
        "department": faculty.department.department_name if faculty.department else None,
        "department_id": faculty.department_id,
        "designation": faculty.designation,
        "account_status": faculty.account_status,
        "assigned_subjects": [
            {
                "id": a.subject.id,
                "subject_code": a.subject.subject_code,
                "subject_name": a.subject.subject_name,
                "section": a.section,
            }
            for a in assignments
        ],
    }


@router.get("/me")
def get_me(faculty: CurrentFaculty, db: DbSession) -> dict:
    return ok(faculty_profile(faculty, db), "Faculty profile")


@router.get("/me/assignments")
def assignments(faculty: CurrentFaculty, db: DbSession) -> dict:
    rows = (
        db.query(FacultyAssignment)
        .filter(FacultyAssignment.faculty_id == faculty.id, FacultyAssignment.assignment_status == "ACTIVE")
        .all()
    )
    return ok([
        {
            "id": a.id,
            "faculty_id": a.faculty_id,
            "subject_id": a.subject_id,
            "examination_id": _infer_examination_id(db, a.subject_id),
            "subject_code": a.subject.subject_code,
            "subject_name": a.subject.subject_name,
            "credits": a.subject.credits,
            "branch_id": a.branch_id,
            "semester_id": a.semester_id,
            "academic_year_id": a.academic_year_id,
            "section": a.section,
            "assignment_status": a.assignment_status,
            "internal_max_marks": a.subject.internal_max_marks,
            "external_max_marks": a.subject.external_max_marks,
            "assessment_configuration": a.subject.assessment_configuration,
        }
        for a in rows
    ], "Assigned subjects")


@router.get("/me/classes")
def classes(faculty: CurrentFaculty, db: DbSession) -> dict:
    rows = (
        db.query(FacultyAssignment)
        .filter(FacultyAssignment.faculty_id == faculty.id, FacultyAssignment.assignment_status == "ACTIVE")
        .all()
    )
    result = []
    seen: set = set()
    for a in rows:
        department_id, branch_id, semester_number = _assignment_scope(db, a)
        key = (department_id, branch_id, semester_number, a.section, a.academic_year_id)
        if key in seen:
            continue
        seen.add(key)
        student_query = db.query(Student).filter(Student.enrollment_status == "ACTIVE")
        if department_id:
            student_query = student_query.filter(Student.department_id == department_id)
        if branch_id:
            student_query = student_query.filter(Student.branch_id == branch_id)
        if semester_number:
            student_query = student_query.filter(Student.current_semester == semester_number)
        if a.section:
            student_query = student_query.filter(Student.section == a.section)
        result.append({
            "department_id": department_id,
            "branch_id": branch_id,
            "semester": semester_number,
            "section": a.section,
            "academic_year_id": a.academic_year_id,
            "student_count": student_query.count(),
            "subject_ids": [
                x.subject_id for x in rows
                if _assignment_scope(db, x) == (department_id, branch_id, semester_number)
                and x.section == a.section and x.academic_year_id == a.academic_year_id
            ],
        })
    return ok(result, "Assigned classes")


@router.get("/me/students")
def students(
    faculty: CurrentFaculty,
    db: DbSession,
    subject_id: UUID | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    assignments = (
        db.query(FacultyAssignment)
        .filter(FacultyAssignment.faculty_id == faculty.id, FacultyAssignment.assignment_status == "ACTIVE")
    )
    if subject_id:
        assignment_rows = [assert_assigned(db, faculty.id, subject_id)]
    else:
        assignment_rows = assignments.all()
    if not assignment_rows:
        return ok(Page.build([], 0, *get_pagination(page, page_size)).model_dump(mode="json"), "Assigned students")

    # Each assignment contributes an exact department/branch/semester/section
    # scope. Combine them with OR so a faculty member with two branches never
    # sees students from an unassigned branch that shares the department.
    scope_filters = []
    for assignment in assignment_rows:
        department_id, branch_id, semester_number = _assignment_scope(db, assignment)
        conditions = []
        if department_id:
            conditions.append(Student.department_id == department_id)
        if branch_id:
            conditions.append(Student.branch_id == branch_id)
        if semester_number:
            conditions.append(Student.current_semester == semester_number)
        if assignment.section:
            conditions.append(Student.section == assignment.section)
        scope_filters.append(and_(*conditions))
    query = db.query(Student).filter(
        Student.enrollment_status == "ACTIVE", or_(*scope_filters)
    )
    if search:
        query = query.filter(
            or_(Student.full_name.ilike(f"%{search}%"), Student.roll_number.ilike(f"%{search}%"))
        )
    page, page_size = get_pagination(page, page_size)
    total = query.count()
    rows = query.order_by(Student.roll_number).offset((page - 1) * page_size).limit(page_size).all()
    items = [
        {
            "id": s.id,
            "roll_number": s.roll_number,
            "full_name": s.full_name,
            "email": s.user.email,
            "branch": s.branch.branch_name if s.branch else None,
            "semester": s.current_semester,
            "section": s.section,
        }
        for s in rows
    ]
    return ok(Page.build(items, total, page, page_size).model_dump(mode="json"), "Assigned students")


def _mark_out(mark: InternalMark) -> dict:
    return {
        "id": mark.id,
        "student_id": mark.student_id,
        "student_name": mark.student.full_name,
        "roll_number": mark.student.roll_number,
        "subject_id": mark.subject_id,
        "subject_code": mark.subject.subject_code,
        "subject_name": mark.subject.subject_name,
        "component_marks": mark.component_marks,
        "mid1_marks": as_number(mark.mid1_marks),
        "mid2_marks": as_number(mark.mid2_marks),
        "assignments_marks": as_number(mark.assignments_marks),
        "total_marks": as_number(mark.total_marks),
        "max_marks": mark.max_marks,
        "status": mark.status,
        "submitted_at": mark.submitted_at,
    }


@router.get("/me/internal-marks")
def internal_marks(faculty: CurrentFaculty, db: DbSession, subject_id: UUID | None = None) -> dict:
    assignment_query = db.query(FacultyAssignment).filter(
        FacultyAssignment.faculty_id == faculty.id, FacultyAssignment.assignment_status == "ACTIVE"
    )
    if subject_id:
        assert_assigned(db, faculty.id, subject_id)
        assignment_query = assignment_query.filter(FacultyAssignment.subject_id == subject_id)
    subject_ids = [a.subject_id for a in assignment_query.all()]
    if not subject_ids:
        return ok([], "Internal marks")
    marks = (
        db.query(InternalMark)
        .filter(InternalMark.faculty_id == faculty.id, InternalMark.subject_id.in_(subject_ids))
        .order_by(InternalMark.subject_id, InternalMark.student_id)
        .all()
    )
    return ok([_mark_out(m) for m in marks], "Internal marks")


@router.post("/me/internal-marks")
def save_marks(payload: BulkMarksIn, faculty: CurrentFaculty, user: CurrentUser, db: DbSession) -> dict:
    """Save MID-1/25, MID-2/25 and Assignments/5 with an authoritative total out of 30."""
    assignment = assert_assigned(db, faculty.id, payload.subject_id)
    subject = db.get(Subject, payload.subject_id)
    if not subject:
        raise NotFoundError("Subject not found")
    examination_id = _resolve_examination_id(db, payload.subject_id, payload.examination_id)
    saved: list[InternalMark] = []
    totals: list[float] = []
    for entry in payload.entries:
        student = db.get(Student, entry.student_id)
        if not student:
            raise ValidationError(f"Student {entry.student_id} not found")
        _validate_scope(assignment, student, db)
        mid1, mid2, assignments = validate_components(
            entry.mid1_marks, entry.mid2_marks, entry.assignments_marks
        )
        total = calculate_internal_total(mid1, mid2, assignments)
        if total > subject.internal_max_marks:
            raise ValidationError(f"Calculated internal marks exceed {subject.internal_max_marks}")
        mark = (
            db.query(InternalMark)
            .filter_by(student_id=entry.student_id, subject_id=payload.subject_id, examination_id=examination_id)
            .first()
        )
        if mark and mark.status in (SubmissionStatus.SUBMITTED, SubmissionStatus.VERIFIED, SubmissionStatus.LOCKED):
            raise ConflictError("Marks are submitted or locked and cannot be modified")
        if not mark:
            mark = InternalMark(
                student_id=entry.student_id,
                subject_id=payload.subject_id,
                examination_id=examination_id,
                faculty_id=faculty.id,
                max_marks=subject.internal_max_marks,
            )
            db.add(mark)
        mark.component_marks = component_marks(mid1, mid2, assignments)
        mark.mid1_marks = mid1
        mark.mid2_marks = mid2
        mark.assignments_marks = assignments
        mark.total_marks = total
        mark.max_marks = subject.internal_max_marks
        mark.academic_year_id = assignment.academic_year_id
        mark.semester_id = assignment.semester_id or subject.semester_id
        mark.status = SubmissionStatus.DRAFT if entry.save_as_draft else SubmissionStatus.IN_PROGRESS
        mark.faculty_id = faculty.id
        db.query(InternalMarkComponent).filter_by(internal_mark_id=mark.id).delete()
        db.flush()
        for name, maximum in INTERNAL_COMPONENTS:
            db.add(InternalMarkComponent(
                internal_mark_id=mark.id, name=name,
                marks_obtained={"MID-1": mid1, "MID-2": mid2, "Assignments": assignments}[name],
                max_marks=int(maximum),
            ))
        saved.append(mark)
        totals.append(total)
    log_action(
        db, user=user, action="INTERNAL_MARKS_SAVED", entity_type="InternalMark",
        entity_id=str(payload.subject_id),
        new={"count": len(saved), "totals": totals, "formula": "best_mid*0.8 + other_mid*0.2 + assignments"},
    )
    db.commit()
    return ok({"saved": len(saved), "totals": totals}, "Marks saved")


def _validate_scope(assignment: FacultyAssignment, student: Student, db: Session) -> None:
    """Fail closed against the subject's department, branch and semester."""
    department_id, branch_id, semester_number = _assignment_scope(db, assignment)
    if department_id and student.department_id != department_id:
        raise ForbiddenError("Student is outside your assigned department")
    if branch_id and student.branch_id != branch_id:
        raise ForbiddenError("Student is outside your assigned branch")
    if semester_number and student.current_semester != semester_number:
        raise ForbiddenError("Student is outside your assigned semester")
    if assignment.section and student.section != assignment.section:
        raise ForbiddenError("Student is outside your assigned section")


@router.get("/me/marks-submissions")
def marks_submissions(faculty: CurrentFaculty, db: DbSession) -> dict:
    rows = (
        db.query(MarksSubmission)
        .filter(MarksSubmission.faculty_id == faculty.id)
        .order_by(MarksSubmission.created_at.desc())
        .all()
    )
    return ok([
        {
            "id": r.id,
            "faculty_id": r.faculty_id,
            "subject_id": r.subject_id,
            "subject_code": r.subject.subject_code,
            "subject_name": r.subject.subject_name,
            "status": r.status,
            "submitted_at": r.submitted_at,
            "review_note": r.review_note,
        }
        for r in rows
    ], "Marks submissions")


@router.post("/me/marks-submissions")
def submit_marks(payload: BulkMarksIn, faculty: CurrentFaculty, user: CurrentUser, db: DbSession) -> dict:
    """Validate and submit marks to the Examination Admin in one transaction."""
    assignment = assert_assigned(db, faculty.id, payload.subject_id)
    subject = db.get(Subject, payload.subject_id)
    if not subject:
        raise NotFoundError("Subject not found")
    if not payload.entries:
        raise ValidationError("At least one student must be included")
    examination_id = _resolve_examination_id(db, payload.subject_id, payload.examination_id)
    marks_by_student: dict[UUID, InternalMark] = {}
    for entry in payload.entries:
        student = db.get(Student, entry.student_id)
        if not student:
            raise ValidationError(f"Student {entry.student_id} not found")
        _validate_scope(assignment, student, db)
        mark = (
            db.query(InternalMark)
            .filter_by(student_id=entry.student_id, subject_id=payload.subject_id, examination_id=examination_id)
            .first()
        )
        if not mark:
            raise ValidationError("Save marks as draft before submitting")
        if mark.status in (SubmissionStatus.SUBMITTED, SubmissionStatus.LOCKED):
            raise ConflictError("Marks have already been submitted or locked")
        marks_by_student[entry.student_id] = mark
    submission = MarksSubmission(
        faculty_id=faculty.id,
        subject_id=payload.subject_id,
        examination_id=examination_id,
        section=None,
        status=SubmissionStatus.SUBMITTED,
        submitted_at=datetime.now(timezone.utc),
    )
    db.add(submission)
    db.flush()
    for mark in marks_by_student.values():
        mark.status = SubmissionStatus.SUBMITTED
        mark.submitted_at = submission.submitted_at
    log_action(db, user=user, action="MARKS_SUBMITTED", entity_type="MarksSubmission", entity_id=str(submission.id))
    admins = db.query(User).filter(User.role == "EXAM_ADMIN").all()
    notify_users(
        db, sender=user, user_ids=[a.id for a in admins], title="Internal marks submitted for verification",
        message=f"Marks for {subject.subject_code} were submitted by {faculty.full_name}.",
        category=NotificationCategory.MARKS_SUBMISSION,
    )
    db.commit()
    return ok({"id": submission.id}, "Marks submitted to Examination Admin")


@router.get("/me/correction-requests")
def correction_requests(faculty: CurrentFaculty, db: DbSession) -> dict:
    rows = (
        db.query(StudentMarkCorrectionRequest)
        .filter(StudentMarkCorrectionRequest.faculty_id == faculty.id)
        .order_by(StudentMarkCorrectionRequest.created_at.desc())
        .all()
    )
    visible = [r for r in rows if _can_review(db, faculty.id, r)]
    return ok([
        {
            "id": r.id,
            "student_id": r.student_id,
            "student_name": r.student.full_name,
            "roll_number": r.student.roll_number,
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
        for r in visible
    ], "Correction requests")


def subject_max_marks(db: Session, subject_id: UUID) -> float:
    subject = db.get(Subject, subject_id)
    if not subject:
        raise ValidationError("Subject not found")
    return float(subject.internal_max_marks + subject.external_max_marks)


def _can_review(db: Session, faculty_id: UUID, request: StudentMarkCorrectionRequest) -> bool:
    return (
        db.query(FacultyAssignment)
        .filter_by(faculty_id=faculty_id, subject_id=request.subject_id, assignment_status="ACTIVE")
        .first()
        is not None
    )


@router.patch("/me/correction-requests/{request_id}")
def review_correction(
    request_id: UUID, payload: CorrectionReview, faculty: CurrentFaculty, user: CurrentUser, db: DbSession
) -> dict:
    request = db.get(StudentMarkCorrectionRequest, request_id)
    if not request:
        raise NotFoundError("Correction request not found")
    if not _can_review(db, faculty.id, request):
        raise ForbiddenError("You cannot review this request")
    if request.request_status in (CorrectionStatus.RESOLVED, CorrectionStatus.REJECTED):
        raise ConflictError("This request is already closed")
    if payload.action == "correct" and payload.corrected_marks is None:
        raise ValidationError("Corrected marks are required when correcting marks")
    if payload.action == "correct":
        corrected = float(payload.corrected_marks)
        if corrected > subject_max_marks(db, request.subject_id):
            raise ValidationError("Corrected marks exceed the permitted range for this subject")
        mark = (
            db.query(InternalMark)
            .filter_by(student_id=request.student_id, subject_id=request.subject_id)
            .first()
        )
        if mark and mark.status == SubmissionStatus.LOCKED:
            raise ConflictError("Marks are locked and cannot be corrected by faculty")
        if mark:
            previous = {"total": mark.total_marks}
            mark.total_marks = corrected
            mark.component_marks = {**mark.component_marks, "Corrected total": corrected}
            # A correction invalidates the previous verification; admin must
            # verify the revised total before it can be used for results.
            mark.status = SubmissionStatus.IN_PROGRESS
            log_action(db, user=user, action="MARK_CORRECTED", entity_type="InternalMark", entity_id=str(mark.id), previous=previous, new={"total": corrected, "status": mark.status})
        request.request_status = CorrectionStatus.RESOLVED
    elif payload.action == "reject":
        request.request_status = CorrectionStatus.REJECTED
    elif payload.action == "under_review":
        request.request_status = CorrectionStatus.UNDER_REVIEW
    else:
        request.request_status = CorrectionStatus.RESOLVED
    request.faculty_response = payload.faculty_response
    request.resolved_at = datetime.now(timezone.utc) if request.request_status in (
        CorrectionStatus.RESOLVED, CorrectionStatus.REJECTED
    ) else None
    log_action(db, user=user, action="CORRECTION_REQUEST_REVIEWED", entity_type="StudentMarkCorrectionRequest", entity_id=str(request.id), new={"status": request.request_status})
    student_user = request.student.user
    notify_users(
        db, sender=user, user_ids=[student_user.id], title="Marks correction request updated",
        message=f"Your marks correction request for {request.subject.subject_code} is now {request.request_status}.",
        category=NotificationCategory.MARKS_CORRECTION,
    )
    db.commit()
    return ok({"id": request.id, "status": request.request_status}, "Request updated")


@router.get("/me/timetable")
def faculty_timetable(faculty: CurrentFaculty, db: DbSession) -> dict:
    subject_ids = [
        a.subject_id for a in db.query(FacultyAssignment)
        .filter_by(faculty_id=faculty.id, assignment_status="ACTIVE").all()
    ]
    rows = (
        db.query(ExaminationSchedule)
        .filter(
            ExaminationSchedule.publication_status == PublicationStatus.PUBLISHED,
            ExaminationSchedule.subject_id.in_(subject_ids),
        )
        .order_by(ExaminationSchedule.exam_date)
        .all()
    )
    return ok([
        {
            "id": s.id,
            "subject_code": s.subject.subject_code,
            "subject_name": s.subject.subject_name,
            "exam_date": s.exam_date.isoformat(),
            "start_time": s.start_time.strftime("%H:%M"),
            "end_time": s.end_time.strftime("%H:%M"),
            "session": s.session,
            "venue": s.venue,
        }
        for s in rows
    ], "Published timetable")


@router.get("/me/notifications")
def faculty_notifications(
    faculty: CurrentFaculty, db: DbSession, category: NotificationCategory | None = None,
    unread_only: bool = False, page: int = 1, page_size: int = 20,
) -> dict:
    page, page_size = get_pagination(page, page_size)
    query = (
        db.query(NotificationRecipient)
        .join(Notification, NotificationRecipient.notification_id == Notification.id)
        .filter(NotificationRecipient.recipient_user_id == faculty.user_id)
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
            "read": r.read_at is not None,
            "read_at": r.read_at,
        }
        for r in rows
    ]
    return ok(Page.build(items, total, page, page_size).model_dump(mode="json"), "Notifications")
