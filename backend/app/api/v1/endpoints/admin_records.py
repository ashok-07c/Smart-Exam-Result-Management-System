"""Examination Admin: academic records, student/faculty records, courses, subjects, assignments."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, DbSession, ExamAdmin, get_pagination, get_or_404
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.core.responses import ok
from app.core.security import hash_password
from app.models.academic import (
    AcademicYear,
    Branch,
    Course,
    Department,
    FacultyAssignment,
    Regulation,
    Semester,
    Subject,
)
from app.models.enums import Role
from app.models.examination import Examination, ExaminationRegistration, ExaminationSchedule
from app.models.marks import InternalMark, MarksSubmission, StudentMarkCorrectionRequest
from app.models.notification import AuditLog, Notification
from app.models.result import RecountingRequest, SemesterResult
from app.models.user import Faculty, Student, User
from app.schemas.academic import (
    AssignmentCreate,
    AcademicYearCreate,
    AssignmentUpdate,
    BranchOut,
    CourseCreate,
    DepartmentOut,
    RegulationCreate,
    SubjectCreate,
)
from app.schemas.user import FacultyCreate, FacultyUpdate, StudentCreate, StudentUpdate
from app.services.academic_scope import resolve_subject_scope
from app.services.audit import log_action

router = APIRouter()


def _student_out(student: Student) -> dict:
    return {
        "id": student.id,
        "user_id": student.user_id,
        "roll_number": student.roll_number,
        "full_name": student.full_name,
        "email": student.user.email,
        "department_id": student.department_id,
        "department": student.department.department_name if student.department else None,
        "branch_id": student.branch_id,
        "branch": student.branch.branch_name if student.branch else None,
        "current_semester": student.current_semester,
        "academic_year": student.academic_year,
        "admission_year": student.admission_year,
        "enrollment_status": student.enrollment_status,
        "section": student.section,
    }


def _faculty_out(faculty: Faculty) -> dict:
    return {
        "id": faculty.id,
        "user_id": faculty.user_id,
        "faculty_id": faculty.faculty_id,
        "full_name": faculty.full_name,
        "email": faculty.user.email,
        "department_id": faculty.department_id,
        "department": faculty.department.department_name if faculty.department else None,
        "designation": faculty.designation,
        "account_status": faculty.account_status,
    }


@router.get("/dashboard")
def admin_dashboard(admin: ExamAdmin, db: DbSession) -> dict:
    return ok({
        "total_students": db.query(Student).count(),
        "total_faculty": db.query(Faculty).count(),
        "active_examinations": db.query(Examination).filter(Examination.status == "OPEN").count(),
        "total_registrations": db.query(ExaminationRegistration).count(),
        "pending_marks_submissions": db.query(MarksSubmission).filter_by(status="SUBMITTED").count(),
        "pending_marks_verification": db.query(InternalMark).filter_by(status="SUBMITTED").count(),
        "pending_corrections": db.query(StudentMarkCorrectionRequest).filter(
            StudentMarkCorrectionRequest.request_status.in_(["SUBMITTED", "UNDER_REVIEW"])
        ).count(),
        "results_awaiting_processing": db.query(SemesterResult).filter_by(status="DRAFT").count(),
        "pending_recounting": db.query(RecountingRequest).filter(
            RecountingRequest.request_status.in_(["SUBMITTED", "PENDING_REVIEW", "PROCESSING"])
        ).count(),
        "upcoming_examinations": [
            {
                "id": e.id,
                "name": e.name,
                "exam_type": e.exam_type,
                "registration_deadline": e.registration_deadline.isoformat() if e.registration_deadline else None,
            }
            for e in db.query(Examination).order_by(Examination.registration_deadline).limit(5).all()
        ],
        "recent_activity": [
            {
                "id": r.id,
                "action": r.action,
                "entity_type": r.entity_type,
                "created_at": r.created_at,
            }
            for r in db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(5).all()
        ],
    }, "Examination administration dashboard")


# ---------------------------------------------------------------------------
# Students
# ---------------------------------------------------------------------------
@router.get("/students")
def list_students(
    admin: ExamAdmin, db: DbSession, search: str | None = None, branch_id: UUID | None = None,
    semester: int | None = None, page: int = 1, page_size: int = 20,
) -> dict:
    query = db.query(Student)
    if search:
        query = query.filter(or_(
            Student.full_name.ilike(f"%{search}%"), Student.roll_number.ilike(f"%{search}%")
        ))
    if branch_id:
        query = query.filter(Student.branch_id == branch_id)
    if semester:
        query = query.filter(Student.current_semester == semester)
    page, page_size = get_pagination(page, page_size)
    total = query.count()
    rows = query.order_by(Student.roll_number).offset((page - 1) * page_size).limit(page_size).all()
    return ok({
        "items": [_student_out(s) for s in rows], "total": total, "page": page,
        "page_size": page_size, "pages": max(1, (total + page_size - 1) // page_size),
    }, "Students")


@router.post("/students")
def create_student(payload: StudentCreate, admin: ExamAdmin, db: DbSession) -> dict:
    email = payload.email.lower().strip()
    if db.query(User).filter_by(email=email).first():
        raise ConflictError("A user with this email already exists")
    if db.query(Student).filter_by(roll_number=payload.roll_number).first():
        raise ConflictError("A student with this roll number already exists")
    user = User(
        email=email, password_hash=hash_password(payload.password),
        role=Role.STUDENT, full_name=payload.full_name,
        must_change_password=payload.must_change_password,
    )
    db.add(user)
    db.flush()
    student = Student(
        user_id=user.id, roll_number=payload.roll_number, full_name=payload.full_name,
        department_id=payload.department_id, branch_id=payload.branch_id,
        current_semester=payload.current_semester, academic_year=payload.academic_year,
        admission_year=payload.admission_year, section=payload.section,
    )
    db.add(student)
    log_action(db, user=admin, action="STUDENT_CREATED", entity_type="Student", entity_id=payload.roll_number)
    db.commit()
    return ok(_student_out(student), "Student created")


@router.get("/students/{student_id}")
def get_student(student_id: UUID, admin: ExamAdmin, db: DbSession) -> dict:
    return ok(_student_out(get_or_404(db, Student, student_id)), "Student")


@router.patch("/students/{student_id}")
def update_student(student_id: UUID, payload: StudentUpdate, admin: ExamAdmin, db: DbSession) -> dict:
    student = get_or_404(db, Student, student_id)
    previous = _student_out(student)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(student, field, value)
    log_action(db, user=admin, action="STUDENT_UPDATED", entity_type="Student", entity_id=str(student_id), previous=previous)
    db.commit()
    return ok(_student_out(student), "Student updated")


@router.delete("/students/{student_id}")
def deactivate_student(student_id: UUID, admin: ExamAdmin, db: DbSession) -> dict:
    student = get_or_404(db, Student, student_id)
    student.enrollment_status = "SUSPENDED"
    student.user.account_status = "INACTIVE"
    log_action(db, user=admin, action="STUDENT_DEACTIVATED", entity_type="Student", entity_id=str(student_id))
    db.commit()
    return ok(message="Student account deactivated")


# ---------------------------------------------------------------------------
# Faculty
# ---------------------------------------------------------------------------
@router.get("/faculty")
def list_faculty(
    admin: ExamAdmin, db: DbSession, search: str | None = None, page: int = 1, page_size: int = 20,
) -> dict:
    query = db.query(Faculty)
    if search:
        query = query.filter(or_(
            Faculty.full_name.ilike(f"%{search}%"), Faculty.faculty_id.ilike(f"%{search}%")
        ))
    page, page_size = get_pagination(page, page_size)
    total = query.count()
    rows = query.order_by(Faculty.faculty_id).offset((page - 1) * page_size).limit(page_size).all()
    return ok({
        "items": [_faculty_out(f) for f in rows], "total": total, "page": page,
        "page_size": page_size, "pages": max(1, (total + page_size - 1) // page_size),
    }, "Faculty")


@router.post("/faculty")
def create_faculty(payload: FacultyCreate, admin: ExamAdmin, db: DbSession) -> dict:
    email = payload.email.lower().strip()
    if db.query(User).filter_by(email=email).first():
        raise ConflictError("A user with this email already exists")
    if db.query(Faculty).filter_by(faculty_id=payload.faculty_id).first():
        raise ConflictError("A faculty member with this ID already exists")
    user = User(
        email=email, password_hash=hash_password(payload.password),
        role=Role.FACULTY, full_name=payload.full_name,
    )
    db.add(user)
    db.flush()
    faculty = Faculty(
        user_id=user.id, faculty_id=payload.faculty_id, full_name=payload.full_name,
        department_id=payload.department_id, designation=payload.designation,
    )
    db.add(faculty)
    log_action(db, user=admin, action="FACULTY_CREATED", entity_type="Faculty", entity_id=payload.faculty_id)
    db.commit()
    return ok(_faculty_out(faculty), "Faculty member created")


@router.get("/faculty/{faculty_id}")
def get_faculty(faculty_id: UUID, admin: ExamAdmin, db: DbSession) -> dict:
    return ok(_faculty_out(get_or_404(db, Faculty, faculty_id)), "Faculty member")


@router.patch("/faculty/{faculty_id}")
def update_faculty(faculty_id: UUID, payload: FacultyUpdate, admin: ExamAdmin, db: DbSession) -> dict:
    faculty = get_or_404(db, Faculty, faculty_id)
    previous = _faculty_out(faculty)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(faculty, field, value)
    if payload.account_status:
        faculty.user.account_status = payload.account_status
    log_action(db, user=admin, action="FACULTY_UPDATED", entity_type="Faculty", entity_id=str(faculty_id), previous=previous)
    db.commit()
    return ok(_faculty_out(faculty), "Faculty member updated")


@router.delete("/faculty/{faculty_id}")
def deactivate_faculty(faculty_id: UUID, admin: ExamAdmin, db: DbSession) -> dict:
    faculty = get_or_404(db, Faculty, faculty_id)
    faculty.account_status = "INACTIVE"
    faculty.user.account_status = "INACTIVE"
    log_action(db, user=admin, action="FACULTY_DEACTIVATED", entity_type="Faculty", entity_id=str(faculty_id))
    db.commit()
    return ok(message="Faculty account deactivated")


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------
@router.get("/departments")
def departments(admin: ExamAdmin, db: DbSession) -> dict:
    return ok([DepartmentOut.model_validate(d).model_dump() for d in db.query(Department).all()], "Departments")


@router.get("/branches")
def branches(admin: ExamAdmin, db: DbSession) -> dict:
    return ok([BranchOut.model_validate(b).model_dump() for b in db.query(Branch).all()], "Branches")


@router.get("/academic-years")
def academic_years(admin: ExamAdmin, db: DbSession) -> dict:
    return ok([
        {"id": y.id, "academic_year_name": y.academic_year_name, "status": y.status}
        for y in db.query(AcademicYear).all()
    ], "Academic years")


@router.post("/academic-years")
def create_academic_year(payload: AcademicYearCreate, admin: ExamAdmin, db: DbSession) -> dict:
    if db.query(AcademicYear).filter_by(academic_year_name=payload.academic_year_name).first():
        raise ConflictError("Academic year already exists")
    for active in db.query(AcademicYear).filter_by(status="ACTIVE").all():
        active.status = "ARCHIVED"
    year = AcademicYear(**payload.model_dump(), status="ACTIVE")
    db.add(year)
    log_action(db, user=admin, action="ACADEMIC_YEAR_CREATED", entity_type="AcademicYear", entity_id=payload.academic_year_name)
    db.commit()
    return ok({"id": year.id}, "Academic year created")


@router.get("/semesters")
def semesters(admin: ExamAdmin, db: DbSession) -> dict:
    return ok([
        {"id": s.id, "semester_number": s.semester_number, "academic_year_id": s.academic_year_id, "regulation_id": s.regulation_id}
        for s in db.query(Semester).order_by(Semester.semester_number).all()
    ], "Semesters")


@router.get("/regulations")
def regulations(admin: ExamAdmin, db: DbSession) -> dict:
    return ok([
        {
            "id": r.id, "regulation_name": r.regulation_name, "effective_year": r.effective_year,
            "grade_rules": r.grade_rules, "pass_rules": r.pass_rules, "calculation_rules": r.calculation_rules,
        }
        for r in db.query(Regulation).all()
    ], "Regulations")


@router.post("/regulations")
def create_regulation(payload: RegulationCreate, admin: ExamAdmin, db: DbSession) -> dict:
    if db.query(Regulation).filter_by(regulation_name=payload.regulation_name).first():
        raise ConflictError("Regulation name already exists")
    regulation = Regulation(**payload.model_dump())
    db.add(regulation)
    log_action(db, user=admin, action="REGULATION_CREATED", entity_type="Regulation", entity_id=payload.regulation_name)
    db.commit()
    return ok({"id": regulation.id}, "Regulation created")


@router.patch("/regulations/{regulation_id}")
def update_regulation(regulation_id: UUID, payload: RegulationCreate, admin: ExamAdmin, db: DbSession) -> dict:
    regulation = get_or_404(db, Regulation, regulation_id)
    previous = {"grade_rules": regulation.grade_rules, "pass_rules": regulation.pass_rules}
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(regulation, field, value)
    log_action(db, user=admin, action="REGULATION_UPDATED", entity_type="Regulation", entity_id=str(regulation_id), previous=previous, new=payload.model_dump())
    db.commit()
    return ok({"id": regulation.id}, "Regulation updated")


# ---------------------------------------------------------------------------
# Courses and subjects
# ---------------------------------------------------------------------------
@router.get("/courses")
def courses(admin: ExamAdmin, db: DbSession) -> dict:
    return ok([
        {
            "id": c.id, "course_name": c.course_name, "course_code": c.course_code,
            "branch_id": c.branch_id, "regulation_id": c.regulation_id, "duration_years": c.duration_years,
        }
        for c in db.query(Course).all()
    ], "Courses")


@router.post("/courses")
def create_course(payload: CourseCreate, admin: ExamAdmin, db: DbSession) -> dict:
    data = payload.model_dump()
    data["course_code"] = data["course_code"].strip().upper()
    if db.query(Course).filter_by(course_code=data["course_code"]).first():
        raise ConflictError("Course code already exists")
    course = Course(**data)
    db.add(course)
    log_action(db, user=admin, action="COURSE_CREATED", entity_type="Course", entity_id=payload.course_code)
    db.commit()
    return ok({"id": course.id}, "Course created")


@router.get("/subjects")
def subjects(admin: ExamAdmin, db: DbSession, search: str | None = None, semester_id: UUID | None = None) -> dict:
    query = db.query(Subject)
    if search:
        query = query.filter(or_(
            Subject.subject_code.ilike(f"%{search}%"), Subject.subject_name.ilike(f"%{search}%")
        ))
    if semester_id:
        query = query.filter(Subject.semester_id == semester_id)
    rows = query.order_by(Subject.subject_code).all()
    return ok([
        {
            "id": s.id, "subject_code": s.subject_code, "subject_name": s.subject_name,
            "course_id": s.course_id, "semester_id": s.semester_id, "credits": s.credits,
            "internal_max_marks": s.internal_max_marks, "external_max_marks": s.external_max_marks,
            "subject_type": s.subject_type, "assessment_configuration": s.assessment_configuration,
        }
        for s in rows
    ], "Subjects")


@router.post("/subjects")
def create_subject(payload: SubjectCreate, admin: ExamAdmin, db: DbSession) -> dict:
    if db.query(Subject).filter_by(subject_code=payload.subject_code).first():
        raise ConflictError("Subject code already exists")
    if payload.internal_max_marks + payload.external_max_marks <= 0:
        raise ValidationError("Total maximum marks must be greater than zero")
    subject = Subject(**payload.model_dump())
    db.add(subject)
    log_action(db, user=admin, action="SUBJECT_CREATED", entity_type="Subject", entity_id=payload.subject_code, new=payload.model_dump())
    db.commit()
    return ok({"id": subject.id}, "Subject created")


@router.get("/subjects/{subject_id}")
def get_subject(subject_id: UUID, admin: ExamAdmin, db: DbSession) -> dict:
    return ok(get_or_404(db, Subject, subject_id).__dict__, "Subject")


@router.patch("/subjects/{subject_id}")
def update_subject(subject_id: UUID, payload: SubjectCreate, admin: ExamAdmin, db: DbSession) -> dict:
    subject = get_or_404(db, Subject, subject_id)
    previous = subject.__dict__.copy()
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(subject, field, value)
    log_action(db, user=admin, action="SUBJECT_UPDATED", entity_type="Subject", entity_id=str(subject_id), previous=previous, new=payload.model_dump())
    db.commit()
    return ok(message="Subject updated")


@router.delete("/subjects/{subject_id}")
def delete_subject(subject_id: UUID, admin: ExamAdmin, db: DbSession) -> dict:
    subject = get_or_404(db, Subject, subject_id)
    if (
        db.query(InternalMark).filter_by(subject_id=subject_id).first()
        or db.query(FacultyAssignment).filter_by(subject_id=subject_id).first()
        or db.query(ExaminationSchedule).filter_by(subject_id=subject_id).first()
    ):
        raise ConflictError("Subject is referenced by marks, assignments or schedules and cannot be deleted")
    db.delete(subject)
    log_action(db, user=admin, action="SUBJECT_DELETED", entity_type="Subject", entity_id=str(subject_id))
    db.commit()
    return ok(message="Subject deleted")


# ---------------------------------------------------------------------------
# Faculty assignments
# ---------------------------------------------------------------------------
@router.get("/faculty-assignments")
def list_assignments(
    admin: ExamAdmin, db: DbSession, faculty_id: UUID | None = None, subject_id: UUID | None = None,
    branch_id: UUID | None = None, semester_id: UUID | None = None, academic_year_id: UUID | None = None,
) -> dict:
    query = db.query(FacultyAssignment)
    for field, value in {
        "faculty_id": faculty_id, "subject_id": subject_id, "branch_id": branch_id,
        "semester_id": semester_id, "academic_year_id": academic_year_id,
    }.items():
        if value:
            query = query.filter(getattr(FacultyAssignment, field) == value)
    rows = query.all()
    return ok([
        {
            "id": a.id, "faculty_id": a.faculty_id, "subject_id": a.subject_id,
            "branch_id": a.branch_id, "semester_id": a.semester_id,
            "academic_year_id": a.academic_year_id, "section": a.section,
            "assignment_status": a.assignment_status,
            # Flat display fields keep the assignment table readable without
            # requiring the client to unwrap the nested subject object.
            "faculty_name": a.faculty.full_name,
            "faculty_code": a.faculty.faculty_id,
            "department": a.faculty.department.department_name if a.faculty.department else None,
            "subject_code": a.subject.subject_code,
            "subject_name": a.subject.subject_name,
            "subject": {
                "id": a.subject.id, "subject_code": a.subject.subject_code,
                "subject_name": a.subject.subject_name, "credits": a.subject.credits,
                "internal_max_marks": a.subject.internal_max_marks,
                "external_max_marks": a.subject.external_max_marks,
                "subject_type": a.subject.subject_type, "course_id": a.subject.course_id,
                "semester_id": a.subject.semester_id, "assessment_configuration": a.subject.assessment_configuration,
            },
        }
        for a in rows
    ], "Faculty assignments")


@router.post("/faculty-assignments")
def create_assignment(payload: AssignmentCreate, admin: ExamAdmin, db: DbSession) -> dict:
    faculty_member = db.get(Faculty, payload.faculty_id)
    if not faculty_member:
        raise NotFoundError("Faculty member not found")
    subject = db.get(Subject, payload.subject_id)
    if not subject:
        raise NotFoundError("Subject not found")

    # A faculty member may only be assigned subjects from their own department.
    # The authoritative department is resolved through the subject's course and
    # branch, never from a client-supplied field.
    department_id, branch_id, _ = resolve_subject_scope(db, subject)
    if faculty_member.department_id and department_id and faculty_member.department_id != department_id:
        raise ForbiddenError("Subject does not belong to the faculty member's department")

    data = payload.model_dump()
    data["branch_id"] = branch_id
    data["semester_id"] = subject.semester_id
    if subject.semester_id:
        semester = db.get(Semester, subject.semester_id)
        if semester:
            data["academic_year_id"] = semester.academic_year_id
    duplicate = db.query(FacultyAssignment).filter_by(**data).first()
    if duplicate:
        raise ConflictError("This assignment already exists")
    assignment = FacultyAssignment(**data)
    db.add(assignment)
    log_action(db, user=admin, action="FACULTY_ASSIGNED", entity_type="FacultyAssignment", entity_id=str(payload.subject_id), new=data)
    db.commit()
    return ok({"id": assignment.id}, "Faculty assigned to subject")


@router.patch("/faculty-assignments/{assignment_id}")
def update_assignment(assignment_id: UUID, payload: AssignmentUpdate, admin: ExamAdmin, db: DbSession) -> dict:
    assignment = get_or_404(db, FacultyAssignment, assignment_id)
    previous = assignment.__dict__.copy()
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(assignment, field, value)
    log_action(db, user=admin, action="FACULTY_ASSIGNMENT_UPDATED", entity_type="FacultyAssignment", entity_id=str(assignment_id), previous=previous)
    db.commit()
    return ok(message="Assignment updated")


@router.delete("/faculty-assignments/{assignment_id}")
def remove_assignment(assignment_id: UUID, admin: ExamAdmin, db: DbSession) -> dict:
    assignment = get_or_404(db, FacultyAssignment, assignment_id)
    assignment.assignment_status = "INACTIVE"
    log_action(db, user=admin, action="FACULTY_ASSIGNMENT_REMOVED", entity_type="FacultyAssignment", entity_id=str(assignment_id))
    db.commit()
    return ok(message="Assignment removed")
