"""Database seeding.

The default seed loads the supplied institution data from ``app/data``. The
small demo dataset used by pytest lives in ``seed_test_db`` and is never used
by the running application.
"""
from __future__ import annotations

import argparse
import csv
import os
import re
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database.session import SessionLocal, Base, engine
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
from app.models.enums import ExamType, NotificationCategory, PublicationStatus, Role, SubmissionStatus, SubjectType
from app.models.examination import Examination, ExaminationRegistration, ExaminationSchedule, ExaminationSubject, RegistrationSubject
from app.models.marks import InternalMark
from app.models.misc import HallTicket
from app.models.notification import Notification, NotificationRecipient
from app.models.result import ExternalMark
from app.models.user import Faculty, Student, User
from app.services.internal_marks import calculate_internal_total

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

# Course metadata. AI&ML remains a selectable course, but no people or subjects
# were supplied for it, so it is created as an empty academic structure.
BRANCH_META: dict[str, dict[str, str]] = {
    "CSE": {
        "department": "Computer Science & Engineering",
        "branch": "Computer Science & Engineering",
        "course": "B.Tech Computer Science & Engineering",
        "code": "CSE",
    },
    "ECE": {
        "department": "Electronics & Communication Engineering",
        "branch": "Electronics & Communication Engineering",
        "course": "B.Tech Electronics & Communication Engineering",
        "code": "ECE",
    },
    "EEE": {
        "department": "Electrical & Electronics Engineering",
        "branch": "Electrical & Electronics Engineering",
        "course": "B.Tech Electrical & Electronics Engineering",
        "code": "EEE",
    },
    "MECHANICAL": {
        "department": "Mechanical Engineering",
        "branch": "Mechanical Engineering",
        "course": "B.Tech Mechanical Engineering",
        "code": "MECH",
    },
    "CIVIL": {
        "department": "Civil Engineering",
        "branch": "Civil Engineering",
        "course": "B.Tech Civil Engineering",
        "code": "CIVIL",
    },
    "AI&ML": {
        "department": "Artificial Intelligence & Machine Learning",
        "branch": "Artificial Intelligence & Machine Learning",
        "course": "B.Tech Artificial Intelligence & Machine Learning",
        "code": "AI&ML",
    },
}

# ---------------------------------------------------------------------------
# Pytest fixture data only — never used by the running application.
# ---------------------------------------------------------------------------
TEST_ACCOUNTS = {
    "admin@example.com": "Admin@123",
    "faculty@example.com": "Faculty@123",
    "student@example.com": "Student@123",
    "student2@example.com": "Student@123",
    "tempstudent@example.com": "Temp@123",
}
TEST_COURSES = ("CSE", "ECE", "EEE", "MECH", "CIVIL", "AI&ML")


def _grade_config() -> dict:
    return {"grade_rules": {}, "pass_rules": {}, "calculation_rules": {}}


def seed_test_db(db: Session) -> None:
    """Seed the isolated fixture dataset used only by the pytest suite."""
    if db.query(User).count() > 0:
        print("Database already contains users; test fixture seed skipped.")
        return

    now = datetime.now(timezone.utc)
    dept = Department(id=uuid4(), department_name="Computer Science & Engineering", department_code="CSE")
    branch = Branch(id=uuid4(), branch_name="Computer Science & Engineering", branch_code="CSE", department_id=dept.id)
    years = [
        AcademicYear(
            id=uuid4(), academic_year_name="2023-24", start_date=date(2023, 8, 1),
            end_date=date(2024, 7, 31), status="ARCHIVED",
        ),
        AcademicYear(
            id=uuid4(), academic_year_name="2024-25", start_date=date(2024, 8, 1),
            end_date=date(2025, 7, 31), status="ARCHIVED",
        ),
        AcademicYear(
            id=uuid4(), academic_year_name="2025-26", start_date=date(2025, 8, 1),
            end_date=date(2026, 7, 31), status="ARCHIVED",
        ),
        AcademicYear(
            id=uuid4(), academic_year_name="2026-27", start_date=date(2026, 8, 1),
            end_date=date(2027, 7, 31), status="ACTIVE",
        ),
    ]
    # Existing fixture records stay in 2025-26; 2026-27 is available as the
    # current academic year for new work.
    year = years[2]
    config = _grade_config()
    regulation = Regulation(
        id=uuid4(), regulation_name="TEST-2025", effective_year="2025",
        grade_rules=config["grade_rules"], pass_rules=config["pass_rules"],
        calculation_rules=config["calculation_rules"],
    )
    semesters = [
        Semester(id=uuid4(), semester_number=i, academic_year_id=year.id, regulation_id=regulation.id)
        for i in range(1, 9)
    ]
    db.add_all([dept, branch, *years, regulation, *semesters])
    db.flush()

    course_names = {
        "CSE": "B.Tech Computer Science & Engineering",
        "ECE": "B.Tech Electronics & Communication Engineering",
        "EEE": "B.Tech Electrical & Electronics Engineering",
        "MECH": "B.Tech Mechanical Engineering",
        "CIVIL": "B.Tech Civil Engineering",
        "AI&ML": "B.Tech Artificial Intelligence & Machine Learning",
    }
    courses = [
        Course(
            id=uuid4(), course_name=course_names[code], course_code=code,
            branch_id=branch.id if code == "CSE" else None,
            regulation_id=regulation.id, duration_years=4,
        )
        for code in TEST_COURSES
    ]
    db.add_all(courses)
    db.flush()
    course = courses[0]
    subjects = [
        Subject(
            id=uuid4(), subject_code="CS301", subject_name="Data Structures", course_id=course.id, semester_id=semesters[2].id,
            credits=4, internal_max_marks=30, external_max_marks=70, subject_type=SubjectType.THEORY,
            assessment_configuration={"components": [
                {"name": "MID-1", "max_marks": 25},
                {"name": "MID-2", "max_marks": 25},
                {"name": "Assignments", "max_marks": 5},
            ]},
        ),
        Subject(
            id=uuid4(), subject_code="CS302", subject_name="Operating Systems", course_id=course.id, semester_id=semesters[2].id,
            credits=3, internal_max_marks=30, external_max_marks=70, subject_type=SubjectType.THEORY,
            assessment_configuration={"components": [
                {"name": "MID-1", "max_marks": 25},
                {"name": "MID-2", "max_marks": 25},
                {"name": "Assignments", "max_marks": 5},
            ]},
        ),
        Subject(
            id=uuid4(), subject_code="CS303", subject_name="Database Management Systems", course_id=course.id, semester_id=semesters[2].id,
            credits=3, internal_max_marks=30, external_max_marks=70, subject_type=SubjectType.THEORY,
            assessment_configuration={"components": [
                {"name": "MID-1", "max_marks": 25},
                {"name": "MID-2", "max_marks": 25},
                {"name": "Assignments", "max_marks": 5},
            ]},
        ),
    ]
    db.add_all(subjects)
    db.flush()

    admin = User(
        id=uuid4(), email="admin@example.com", password_hash=hash_password("Admin@123"),
        role=Role.EXAM_ADMIN, full_name="Examination Administrator",
    )
    faculty_user = User(
        id=uuid4(), email="faculty@example.com", password_hash=hash_password("Faculty@123"),
        role=Role.FACULTY, full_name="Dr. Anita Sharma",
    )
    student_users = [
        User(id=uuid4(), email="student@example.com", password_hash=hash_password("Student@123"), role=Role.STUDENT, full_name="Arjun Kumar"),
        User(id=uuid4(), email="student2@example.com", password_hash=hash_password("Student@123"), role=Role.STUDENT, full_name="Priya Singh"),
        User(
            id=uuid4(), email="tempstudent@example.com", password_hash=hash_password("Temp@123"),
            role=Role.STUDENT, full_name="Rahul Verma", must_change_password=True,
        ),
    ]
    db.add_all([admin, faculty_user, *student_users])
    db.flush()

    faculty = Faculty(
        id=uuid4(), user_id=faculty_user.id, faculty_id="FAC001", full_name="Dr. Anita Sharma",
        department_id=dept.id, designation="Associate Professor",
    )
    db.add(faculty)
    db.flush()

    students = [
        Student(
            id=uuid4(), user_id=student_users[0].id, roll_number="21CS001", full_name="Arjun Kumar",
            department_id=dept.id, branch_id=branch.id, current_semester=3, academic_year="2025-26",
            admission_year="2021-22", section="A",
        ),
        Student(
            id=uuid4(), user_id=student_users[1].id, roll_number="21CS002", full_name="Priya Singh",
            department_id=dept.id, branch_id=branch.id, current_semester=3, academic_year="2025-26",
            admission_year="2021-22", section="A",
        ),
        Student(
            id=uuid4(), user_id=student_users[2].id, roll_number="21CS003", full_name="Rahul Verma",
            department_id=dept.id, branch_id=branch.id, current_semester=3, academic_year="2025-26",
            admission_year="2021-22", section="A",
        ),
    ]
    db.add_all(students)
    db.flush()

    db.add_all([
        FacultyAssignment(
            faculty_id=faculty.id, subject_id=s.id, branch_id=branch.id,
            semester_id=semesters[2].id, academic_year_id=year.id, section="A",
        )
        for s in subjects
    ])

    exam = Examination(
        id=uuid4(), name="Regular Semester III - 2025-26", exam_type=ExamType.REGULAR,
        academic_year_id=year.id, semester_id=semesters[2].id, branch_id=None,
        registration_start=now - timedelta(days=5),
        registration_deadline=now + timedelta(days=20),
        eligibility_criteria={
            "eligible_semesters": [3],
            "max_backlogs": 4, "require_backlog": False,
            "recounting_until": (now + timedelta(days=40)).isoformat(),
        },
        status="OPEN", created_by=admin.id,
    )
    db.add(exam)
    db.flush()
    for subject in subjects:
        db.add(ExaminationSubject(examination_id=exam.id, subject_id=subject.id))
    db.flush()

    registration = ExaminationRegistration(
        examination_id=exam.id, student_id=students[0].id, status="SUBMITTED", submitted_at=now
    )
    db.add(registration)
    db.flush()
    for subject in subjects:
        db.add(RegistrationSubject(registration_id=registration.id, subject_id=subject.id))

    for index, subject in enumerate(subjects):
        db.add(ExaminationSchedule(
            examination_id=exam.id, subject_id=subject.id, branch_id=branch.id,
            semester_id=semesters[2].id, academic_year_id=year.id,
            exam_date=date.today() + timedelta(days=30 + index * 2),
            start_time=time(9, 30), end_time=time(12, 30), session="FORENOON",
            venue="Room A-101", publication_status=PublicationStatus.PUBLISHED,
        ))

    ticket = HallTicket(
        student_id=students[0].id, examination_id=exam.id,
        ticket_number="HT-REG-DEMO001", generated_by=admin.id, issued_at=now,
    )
    db.add(ticket)

    for student in students:
        for subject in subjects:
            db.add(InternalMark(
                student_id=student.id, subject_id=subject.id, examination_id=exam.id,
                faculty_id=faculty.id,
                component_marks={"MID-1": 20, "MID-2": 24, "Assignments": 4},
                mid1_marks=20, mid2_marks=24, assignments_marks=4,
                total_marks=calculate_internal_total(20, 24, 4), max_marks=30, status=SubmissionStatus.VERIFIED,
                academic_year_id=year.id, semester_id=semesters[2].id,
                verified_at=now, verified_by=admin.id,
            ))
            db.add(ExternalMark(
                student_id=student.id, subject_id=subject.id, examination_id=exam.id,
                marks_obtained=52 if subject.subject_code != "CS302" else 33,
                max_marks=70, entered_by=admin.id,
            ))

    notification = Notification(
        id=uuid4(), title="Semester III regular examination registration is open",
        message="Registration for the Regular Semester III examinations is open. Please submit your subjects before the deadline.",
        category=NotificationCategory.EXAM_REGISTRATION, sender_id=admin.id,
        audience_type="ALL_STUDENTS", published_at=now,
    )
    db.add(notification)
    db.flush()
    for student in students:
        db.add(NotificationRecipient(notification_id=notification.id, recipient_user_id=student.user_id))

    db.commit()
    print("Test fixture data seeded (pytest only; not used by the running app):")
    for email, password in TEST_ACCOUNTS.items():
        print(f"  {email} / {password}")


# ---------------------------------------------------------------------------
# Institution data — the default seed used by the running application.
# ---------------------------------------------------------------------------
def _read_rows(filename: str) -> list[dict[str, str]]:
    with (DATA_DIR / filename).open("r", encoding="utf-8-sig", newline="") as handle:
        return [
            {key.strip(): (value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(handle)
            if any((value or "").strip() for value in row.values())
        ]


def _branch_code(supplied: str) -> str:
    code = supplied.strip().upper()
    if code == "MECHANICAL":
        return "MECHANICAL"
    if code not in BRANCH_META:
        raise ValueError(f"Unknown branch in supplied data: {supplied!r}")
    return code


def _course_code(supplied: str) -> str:
    return BRANCH_META[_branch_code(supplied)]["code"]


def _semester_from_subject_code(code: str) -> int:
    match = re.search(r"\d", code)
    if not match:
        raise ValueError(f"Cannot infer semester from subject code {code!r}")
    semester = int(match.group())
    if not 1 <= semester <= 8:
        raise ValueError(f"Invalid semester {semester} inferred from {code!r}")
    return semester


def _email_slug(name: str) -> str:
    without_title = re.sub(r"^(dr|mr|mrs|ms)\.\s*", "", name.strip(), flags=re.IGNORECASE)
    slug = re.sub(r"[^a-z0-9]+", ".", without_title.lower()).strip(".")
    return slug or "user"


def _initial_password(full_name: str, role: Role | None = None) -> str:
    """Return the simple seeded password: ``name@123``.

    Admin is always ``admin@123``. For people, titles are removed and spaces
    are replaced with dots, e.g. ``Dr. Suresh Babu`` -> ``suresh.babu@123``.
    These are deliberately easy local-seed credentials, not production secrets.
    """
    if role == Role.EXAM_ADMIN:
        return "admin@123"
    cleaned = re.sub(r"^(dr|mr|mrs|ms)\.\s*", "", full_name.strip(), flags=re.IGNORECASE)
    slug = re.sub(r"[^a-z0-9]+", ".", cleaned.lower()).strip(".")
    return f"{slug or 'user'}@123"


def _component_config() -> dict:
    return {"components": [
        {"name": "MID-1", "max_marks": 25},
        {"name": "MID-2", "max_marks": 25},
        {"name": "Assignments", "max_marks": 5},
    ]}


def _write_credentials(path: Path, credentials: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["role", "name", "identifier", "email", "password"])
        writer.writeheader()
        writer.writerows(credentials)
    try:
        path.chmod(0o600)
    except OSError:
        pass


def seed_institution_db(db: Session, credentials_out: Path | None = None) -> list[dict[str, str]]:
    """Seed the supplied institution data. Refuses to mix with existing users."""
    if db.query(User).count() > 0:
        raise RuntimeError(
            "Database already contains users. Use a fresh database or run "
            "`alembic downgrade base && alembic upgrade head` before seeding institution data."
        )

    faculty_rows = _read_rows("faculty.csv")
    subject_rows = _read_rows("subjects.csv")
    student_rows = _read_rows("students.csv")
    if not (faculty_rows and subject_rows and student_rows):
        raise RuntimeError("Institution data files are empty or missing")

    departments = {
        code: Department(id=uuid4(), department_name=meta["department"], department_code=meta["code"])
        for code, meta in BRANCH_META.items()
    }
    branches = {
        code: Branch(
            id=uuid4(), branch_name=meta["branch"], branch_code=meta["code"], department_id=departments[code].id
        )
        for code, meta in BRANCH_META.items()
    }
    # Alembic's workflow migration already inserts 2026-27. Reuse any years it
    # created instead of inserting duplicate names into the unique index.
    year_specs = [
        ("2023-24", date(2023, 8, 1), date(2024, 7, 31), "ARCHIVED"),
        ("2024-25", date(2024, 8, 1), date(2025, 7, 31), "ARCHIVED"),
        ("2025-26", date(2025, 8, 1), date(2026, 7, 31), "ARCHIVED"),
        ("2026-27", date(2026, 8, 1), date(2027, 7, 31), "ACTIVE"),
    ]
    existing_years = {row.academic_year_name: row for row in db.query(AcademicYear).all()}
    years: list[AcademicYear] = []
    new_years: list[AcademicYear] = []
    for name, start, end, status in year_specs:
        existing = existing_years.get(name)
        if existing:
            years.append(existing)
        else:
            year_row = AcademicYear(
                id=uuid4(), academic_year_name=name, start_date=start,
                end_date=end, status=status,
            )
            years.append(year_row)
            new_years.append(year_row)
    regulation = Regulation(
        id=uuid4(), regulation_name="R2024", effective_year="2024",
        grade_rules={}, pass_rules={}, calculation_rules={},
    )
    year = years[2]
    semesters = {
        number: Semester(id=uuid4(), semester_number=number, academic_year_id=year.id, regulation_id=regulation.id)
        for number in range(1, 9)
    }
    db.add_all([*departments.values(), *branches.values(), *new_years, regulation, *semesters.values()])
    db.flush()

    courses = {
        code: Course(
            id=uuid4(), course_name=meta["course"], course_code=meta["code"],
            branch_id=branches[code].id, regulation_id=regulation.id, duration_years=4,
        )
        for code, meta in BRANCH_META.items()
    }
    db.add_all(courses.values())
    db.flush()

    subjects: list[Subject] = []
    subjects_by_branch: dict[str, list[Subject]] = defaultdict(list)
    branch_semesters: dict[str, set[int]] = defaultdict(set)
    for row in subject_rows:
        supplied_branch = _branch_code(row["branch"])
        semester = _semester_from_subject_code(row["code"])
        subject = Subject(
            id=uuid4(), subject_code=row["code"].upper(), subject_name=row["name"],
            course_id=courses[supplied_branch].id, semester_id=semesters[semester].id,
            credits=4, internal_max_marks=30, external_max_marks=70,
            subject_type=SubjectType.THEORY, assessment_configuration=_component_config(),
        )
        subjects.append(subject)
        subjects_by_branch[supplied_branch].append(subject)
        branch_semesters[supplied_branch].add(semester)
    db.add_all(subjects)
    db.flush()

    credentials: list[dict[str, str]] = []
    used_emails: set[str] = set()

    def new_email(local: str, domain: str) -> str:
        base = f"{local}@{domain}"
        email = base
        suffix = 2
        while email in used_emails:
            email = f"{local}.{suffix}@{domain}"
            suffix += 1
        used_emails.add(email)
        return email

    admin_email = os.getenv("SEED_ADMIN_EMAIL", "admin@jntua.ac.in")
    if admin_email in used_emails:
        raise RuntimeError(f"SEED_ADMIN_EMAIL {admin_email!r} collides with a generated account")
    used_emails.add(admin_email)
    admin_password = _initial_password("Administrator", Role.EXAM_ADMIN)
    admin = User(
        id=uuid4(), email=admin_email, password_hash=hash_password(admin_password),
        role=Role.EXAM_ADMIN, full_name="Examination Administrator",
    )
    db.add(admin)
    credentials.append({
        "role": "EXAM_ADMIN", "name": admin.full_name, "identifier": "administrator",
        "email": admin_email, "password": admin_password,
    })

    faculty_by_branch: dict[str, list[Faculty]] = defaultdict(list)
    branch_counters: dict[str, int] = defaultdict(int)
    for row in faculty_rows:
        supplied_branch = _branch_code(row["branch"])
        branch_counters[supplied_branch] += 1
        email = new_email(
            _email_slug(row["name"]),
            os.getenv("SEED_FACULTY_DOMAIN", "faculty.jntua.ac.in"),
        )
        password = _initial_password(row["name"])
        user = User(
            id=uuid4(), email=email, password_hash=hash_password(password),
            role=Role.FACULTY, full_name=row["name"],
        )
        db.add(user)
        db.flush()
        faculty = Faculty(
            id=uuid4(), user_id=user.id,
            faculty_id=f"FAC-{BRANCH_META[supplied_branch]['code']}-{branch_counters[supplied_branch]:02d}",
            full_name=row["name"], department_id=departments[supplied_branch].id,
            designation="Faculty",
        )
        db.add(faculty)
        faculty_by_branch[supplied_branch].append(faculty)
        credentials.append({
            "role": "FACULTY", "name": row["name"], "identifier": faculty.faculty_id,
            "email": email, "password": password,
        })

    for row in student_rows:
        supplied_branch = _branch_code(row["branch"])
        if len(branch_semesters[supplied_branch]) != 1:
            raise RuntimeError(f"Expected one semester for {supplied_branch} subjects")
        email = new_email(
            row["roll_number"].lower(),
            os.getenv("SEED_STUDENT_DOMAIN", "student.jntua.ac.in"),
        )
        password = _initial_password(row["name"])
        user = User(
            id=uuid4(), email=email, password_hash=hash_password(password),
            role=Role.STUDENT, full_name=row["name"], must_change_password=True,
        )
        db.add(user)
        db.flush()
        student = Student(
            id=uuid4(), user_id=user.id, roll_number=row["roll_number"], full_name=row["name"],
            department_id=departments[supplied_branch].id, branch_id=branches[supplied_branch].id,
            current_semester=next(iter(branch_semesters[supplied_branch])),
            academic_year="2025-26", admission_year="2024-25", section="A",
        )
        db.add(student)
        credentials.append({
            "role": "STUDENT", "name": row["name"], "identifier": row["roll_number"],
            "email": email, "password": password,
        })

    for supplied_branch, branch_subjects in subjects_by_branch.items():
        allocated_faculty = faculty_by_branch.get(supplied_branch, [])
        if len(allocated_faculty) != len(branch_subjects):
            raise RuntimeError(
                f"{supplied_branch}: {len(allocated_faculty)} faculty for {len(branch_subjects)} subjects"
            )
        for faculty, subject in zip(allocated_faculty, branch_subjects):
            if faculty.department_id != departments[supplied_branch].id:
                raise RuntimeError(f"Faculty {faculty.faculty_id} is not in {supplied_branch}")
            if courses[supplied_branch].branch_id != branches[supplied_branch].id:
                raise RuntimeError(f"Course {supplied_branch} is not linked to its branch")
            db.add(FacultyAssignment(
                faculty_id=faculty.id, subject_id=subject.id, branch_id=branches[supplied_branch].id,
                semester_id=subject.semester_id, academic_year_id=year.id, section="A",
                assignment_status="ACTIVE",
            ))

    if credentials_out:
        _write_credentials(credentials_out, credentials)
    db.commit()

    print(
        f"Institution seed complete: {len(faculty_rows)} faculty, {len(subject_rows)} subjects, "
        f"{len(student_rows)} students, {len(credentials)} accounts."
    )
    print(f"Exam admin: {admin_email}")
    if credentials_out:
        print(f"Initial passwords written to {credentials_out} — keep this file secure and distribute privately.")
    else:
        print("Initial passwords (one per account):")
        for row in credentials:
            print(f"  {row['role']:<11} {row['email']} / {row['password']}")
    return credentials


# Backwards-compatible name for callers that expect ``seed_db``.
seed_db = seed_institution_db


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Seed the examination system database")
    parser.add_argument(
        "--test-data", action="store_true",
        help="seed the isolated pytest fixture dataset instead of institution data",
    )
    parser.add_argument(
        "--credentials-out", type=Path,
        help="write initial passwords to this CSV instead of printing them",
    )
    args = parser.parse_args(argv)

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        if args.test_data:
            seed_test_db(session)
        else:
            seed_institution_db(session, args.credentials_out)


if __name__ == "__main__":
    import app.models  # noqa: F401

    main()
