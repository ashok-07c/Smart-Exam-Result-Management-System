"""Tests for the newly specified workflows and centralized grading rules."""
from datetime import datetime, timedelta, timezone
from io import BytesIO
from uuid import uuid4

import pytest

from app.database.session import SessionLocal
from app.models.academic import Branch, Course, Department, Subject
from app.models.enums import SubjectType
from app.services.grading import GradeConfig
from app.services.internal_marks import calculate_internal_total


@pytest.mark.parametrize(
    ("percentage", "expected"),
    [
        (90.01, "S"),
        (90, "A"),
        (80.01, "A"),
        (80, "B"),
        (70, "B"),
        (60.01, "C"),
        (60, "D"),
        (50.01, "D"),
        (50, "E"),
        (40.01, "E"),
        (40, "E"),
        (39.99, "Fail"),
    ],
)
def test_central_grading_boundaries(percentage, expected):
    assert GradeConfig().grade_for(percentage)[0] == expected


@pytest.mark.parametrize(("percentage", "expected"), [(40, True), (39.99, False), (100, True)])
def test_central_pass_rule(percentage, expected):
    assert GradeConfig().is_pass(0, 30, percentage, 70, percentage, 100) is expected


def test_admin_sees_required_courses_and_academic_years_from_2023(client, admin_headers):
    years = client.get("/api/v1/admin/academic-years", headers=admin_headers).json()["data"]
    year_names = {y["academic_year_name"] for y in years}
    assert {"2023-24", "2024-25", "2025-26", "2026-27"}.issubset(year_names)
    assert all(int(name[:4]) >= 2023 for name in year_names)

    courses = client.get("/api/v1/admin/courses", headers=admin_headers).json()["data"]
    assert {c["course_code"] for c in courses} == {"CSE", "ECE", "EEE", "MECH", "CIVIL", "AI&ML"}


def test_admin_can_create_academic_year_only_from_2023(client, admin_headers):
    valid = client.post(
        "/api/v1/admin/academic-years",
        json={"academic_year_name": "2027-28"},
        headers=admin_headers,
    )
    assert valid.status_code == 200, valid.text
    invalid = client.post(
        "/api/v1/admin/academic-years",
        json={"academic_year_name": "2022-23"},
        headers=admin_headers,
    )
    assert invalid.status_code == 422


def test_regulation_create_rejects_legacy_json_rules(client, admin_headers):
    response = client.post(
        "/api/v1/admin/regulations",
        json={
            "regulation_name": "R2026",
            "effective_year": "2026",
            "grade_rules": {"S": 90},
            "pass_rules": {"overall": 40},
            "calculation_rules": {"mode": "credit_weighted"},
        },
        headers=admin_headers,
    )
    assert response.status_code == 422, response.text


def test_external_marks_records_include_context_for_frontend(client, admin_headers):
    response = client.get("/api/v1/admin/marks-management", headers=admin_headers)
    assert response.status_code == 200, response.text
    external = response.json()["data"]["external"]
    assert external
    assert external[0]["examination_name"]
    assert external[0]["academic_year_name"] == "2025-26"
    assert external[0]["student_name"]
    assert external[0]["subject_code"]


def test_external_marks_csv_preview_confirm_and_audit(client, admin_headers):
    exam_id = client.get("/api/v1/admin/examinations", headers=admin_headers).json()["data"][0]["id"]
    csv_content = (
        "rollno,subcode,marks\n"
        "21CS001,CS301,65\n"
        "21CS002,CS301,71\n"
        "DOESNOTEXIST,CS301,60\n"
    ).encode()
    preview = client.post(
        "/api/v1/admin/result-processing/import",
        data={"examination_id": exam_id},
        files={"file": ("external-marks.csv", BytesIO(csv_content), "text/csv")},
        headers=admin_headers,
    )
    assert preview.status_code == 200, preview.text
    data = preview.json()["data"]
    assert data["summary"]["total"] == 3
    assert data["summary"]["invalid"] == 2
    assert data["summary"]["skipped"] == 1
    assert any(row["errors"] for row in data["rows"] if row["rollno"] == "DOESNOTEXIST")
    assert any("0 and 70" in " ".join(row["errors"]) for row in data["rows"] if row["rollno"] == "21CS002")

    confirmed = client.post(
        f"/api/v1/admin/result-processing/import/{data['import_id']}/confirm?overwrite=true",
        headers=admin_headers,
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["data"]["applied"] == 1

    marks = client.get("/api/v1/admin/marks-management", headers=admin_headers).json()["data"]["external"]
    mark = next(m for m in marks if m["roll_number"] == "21CS001" and m["subject_code"] == "CS301")
    assert mark["marks_obtained"] == 65

    logs = client.get("/api/v1/admin/audit-logs", headers=admin_headers).json()["data"]["items"]
    actions = {log["action"] for log in logs}
    assert "EXTERNAL_MARKS_CSV_VALIDATED" in actions
    assert "EXTERNAL_MARKS_IMPORTED" in actions


def test_numeric_mark_correction_flow(client, student_headers, faculty_headers):
    created = client.post(
        "/api/v1/students/me/mark-correction-requests",
        json={
            "subject_code": "cs301",
            "reported_marks": 24.8,
            "suggested_marks": 26.5,
            "explanation": "The assignment component was entered incorrectly.",
        },
        headers=student_headers,
    )
    assert created.status_code == 200, created.text

    student_requests = client.get(
        "/api/v1/students/me/mark-correction-requests", headers=student_headers
    ).json()["data"]
    correction = next(r for r in student_requests if r["subject_code"] == "CS301")
    assert correction["reported_marks"] == 24.8
    assert correction["suggested_marks"] == 26.5

    faculty_requests = client.get(
        "/api/v1/faculty/me/correction-requests", headers=faculty_headers
    ).json()["data"]
    faculty_correction = next(r for r in faculty_requests if r["id"] == correction["id"])
    assert faculty_correction["reported_marks"] == 24.8

    reviewed = client.patch(
        f"/api/v1/faculty/me/correction-requests/{correction['id']}",
        json={"action": "correct", "faculty_response": "Verified and corrected", "corrected_marks": 26.5},
        headers=faculty_headers,
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["data"]["status"] == "RESOLVED"

    student_requests = client.get(
        "/api/v1/students/me/mark-correction-requests", headers=student_headers
    ).json()["data"]
    assert next(r for r in student_requests if r["id"] == correction["id"])["request_status"] == "RESOLVED"


def test_internal_total_rounds_up_to_next_integer():
    # (24 x 0.8) + (20 x 0.2) + 4 = 27.2 -> 28.
    assert calculate_internal_total(20, 24, 4) == 28
    assert calculate_internal_total(25, 25, 5) == 30


def _create_exam(client, admin_headers, name, subject_ids, criteria=None):
    now = datetime.now(timezone.utc)
    response = client.post(
        "/api/v1/admin/examinations",
        json={
            "name": name,
            "exam_type": "REGULAR",
            "registration_start": (now - timedelta(days=1)).isoformat(),
            "registration_deadline": (now + timedelta(days=20)).isoformat(),
            "eligibility_criteria": criteria or {},
            # A legacy client may still send these; the server must ignore them.
            "branch_id": str(uuid4()),
            "semester_id": str(uuid4()),
            "subject_ids": [str(x) for x in subject_ids],
        },
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    exam_id = response.json()["data"]["id"]
    return client.get(f"/api/v1/admin/examinations/{exam_id}", headers=admin_headers).json()["data"]


def test_exam_announcement_is_branchless_and_derives_semester(client, admin_headers):
    subject = client.get("/api/v1/admin/subjects", headers=admin_headers).json()["data"][0]
    course = next(
        c for c in client.get("/api/v1/admin/courses", headers=admin_headers).json()["data"]
        if c["id"] == subject["course_id"]
    )
    exam = _create_exam(
        client, admin_headers, "Common Branchless Exam", [subject["id"]],
        {"eligible_branches": [course["branch_id"]], "eligible_semesters": [1]},
    )
    assert exam["branch_id"] is None
    assert exam["semester_id"] == subject["semester_id"]
    assert not {"eligible_branches", "eligible_semesters", "min_semester"} & set(exam["eligibility_criteria"])


def test_student_subjects_are_limited_to_current_semester(client, admin_headers, student2_headers):
    subjects = client.get("/api/v1/admin/subjects", headers=admin_headers).json()["data"]
    current = next(s for s in subjects if s["subject_code"] == "CS301")
    other_semester = next(
        s for s in client.get("/api/v1/admin/semesters", headers=admin_headers).json()["data"]
        if s["semester_number"] != 3
    )
    created = client.post(
        "/api/v1/admin/subjects",
        json={
            "subject_code": "CS401", "subject_name": "Out of Semester",
            "course_id": current["course_id"], "semester_id": other_semester["id"],
            "credits": 3, "internal_max_marks": 30, "external_max_marks": 70,
            "subject_type": "THEORY", "assessment_configuration": {},
        },
        headers=admin_headers,
    )
    assert created.status_code == 200, created.text
    exam = _create_exam(
        client, admin_headers, "Semester Scope Exam", [current["id"], created.json()["data"]["id"]]
    )
    visible = client.get(
        f"/api/v1/students/me/examinations/{exam['id']}/subjects", headers=student2_headers
    ).json()["data"]
    assert [s["subject_code"] for s in visible] == ["CS301"]


def test_student_cannot_change_academic_context(client, student_headers):
    before = client.get("/api/v1/students/me", headers=student_headers).json()["data"]
    response = client.patch(
        "/api/v1/students/me/profile",
        json={
            "full_name": before["full_name"], "section": "B",
            "current_semester": 12, "academic_year": "2019-20",
            "enrollment_status": "SUSPENDED",
            "department_id": before["department_id"], "branch_id": before["branch_id"],
        },
        headers=student_headers,
    )
    assert response.status_code == 200, response.text
    after = client.get("/api/v1/students/me", headers=student_headers).json()["data"]
    assert after["section"] == "B"
    assert after["current_semester"] == before["current_semester"]
    assert after["academic_year"] == before["academic_year"]
    assert after["enrollment_status"] == before["enrollment_status"]


def _faculty_id(client, admin_headers):
    return client.get("/api/v1/admin/faculty", headers=admin_headers).json()["data"]["items"][0]["id"]


def test_assignment_list_exposes_faculty_and_subject_details(client, admin_headers):
    rows = client.get("/api/v1/admin/faculty-assignments", headers=admin_headers).json()["data"]
    assert rows
    row = next(r for r in rows if r["subject_code"] == "CS301")
    assert row["subject_name"] == "Data Structures"
    assert row["faculty_name"]
    assert row["faculty_code"].startswith("FAC")
    assert row["department"]


def test_assignment_rejects_subject_from_another_department(client, admin_headers):
    with SessionLocal() as db:
        department = Department(id=uuid4(), department_name="Electronics", department_code="ECE-TEST")
        branch = Branch(id=uuid4(), branch_name="Electronics", branch_code="ECE-TEST", department_id=department.id)
        course = Course(
            id=uuid4(), course_name="B.Tech ECE", course_code="ECEPTEST",
            branch_id=branch.id, duration_years=4,
        )
        subject = Subject(
            id=uuid4(), subject_code="EC999", subject_name="Foreign Subject",
            course_id=course.id, credits=3, internal_max_marks=30, external_max_marks=70,
            subject_type=SubjectType.THEORY, assessment_configuration={},
        )
        db.add_all([department, branch, course, subject])
        db.commit()
        subject_id = subject.id
    response = client.post(
        "/api/v1/admin/faculty-assignments",
        json={"faculty_id": _faculty_id(client, admin_headers), "subject_id": str(subject_id)},
        headers=admin_headers,
    )
    assert response.status_code == 403, response.text


def test_faculty_scope_fails_closed_without_resolvable_academic_chain(client, admin_headers, faculty_headers):
    with SessionLocal() as db:
        subject = Subject(
            id=uuid4(), subject_code="NOSCOPE", subject_name="No Academic Scope",
            credits=1, internal_max_marks=30, external_max_marks=70,
            subject_type=SubjectType.THEORY, assessment_configuration={},
        )
        db.add(subject)
        db.commit()
        subject_id = subject.id
    assigned = client.post(
        "/api/v1/admin/faculty-assignments",
        json={"faculty_id": _faculty_id(client, admin_headers), "subject_id": str(subject_id)},
        headers=admin_headers,
    )
    assert assigned.status_code == 200, assigned.text
    response = client.get(
        f"/api/v1/faculty/me/students?subject_id={subject_id}", headers=faculty_headers
    )
    assert response.status_code == 403, response.text

