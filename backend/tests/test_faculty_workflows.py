"""Faculty assignment boundaries and marks workflow tests."""
import uuid

from app.database.session import SessionLocal
from app.models.marks import InternalMark
from tests.conftest import login


def _assignment_and_student(client, faculty_headers):
    assignment = client.get("/api/v1/faculty/me/assignments", headers=faculty_headers).json()["data"][0]
    students = client.get(
        f"/api/v1/faculty/me/students?subject_id={assignment['subject_id']}", headers=faculty_headers
    ).json()["data"]["items"]
    student = students[0]
    # The fixture ships a verified mark for every student/subject pair. Remove
    # this one so the tests can exercise the draft -> submit -> lock path; the
    # endpoint now links drafts to the examination, so it would otherwise be a
    # conflict with that pre-verified row.
    with SessionLocal() as db:
        db.query(InternalMark).filter_by(
            student_id=uuid.UUID(student["id"]), subject_id=uuid.UUID(assignment["subject_id"])
        ).delete()
        db.commit()
    return assignment, student


def _marks_payload(subject_id: str, student_id: str, mid1=20, mid2=24, assignments=4):
    return {
        "subject_id": subject_id,
        "entries": [{
            "student_id": student_id,
            "subject_id": subject_id,
            "mid1_marks": mid1,
            "mid2_marks": mid2,
            "assignments_marks": assignments,
            "save_as_draft": True,
        }],
    }


def test_faculty_sees_only_assigned_subjects(client, faculty_headers, admin_headers):
    assigned = client.get("/api/v1/faculty/me/assignments", headers=faculty_headers).json()["data"]
    all_subjects = client.get("/api/v1/admin/subjects", headers=admin_headers).json()["data"]
    assert len(assigned) == len(all_subjects)
    for a in assigned:
        assert a["subject_id"] in {s["id"] for s in all_subjects}
        assert {c["name"] for c in a["assessment_configuration"]["components"]} == {
            "MID-1", "MID-2", "Assignments"
        }


def test_internal_marks_limit_validation(client, faculty_headers):
    assignment, student = _assignment_and_student(client, faculty_headers)
    response = client.post(
        "/api/v1/faculty/me/internal-marks",
        json=_marks_payload(assignment["subject_id"], student["id"], mid1=99),
        headers=faculty_headers,
    )
    assert response.status_code == 422, response.text
    assert any("mid1_marks" in error["field"] for error in response.json()["errors"])


def test_internal_marks_total_is_calculated_by_backend(client, faculty_headers):
    assignment, student = _assignment_and_student(client, faculty_headers)
    saved = client.post(
        "/api/v1/faculty/me/internal-marks",
        json=_marks_payload(assignment["subject_id"], student["id"]),
        headers=faculty_headers,
    )
    assert saved.status_code == 200, saved.text
    # (24 x 0.8) + (20 x 0.2) + 4 = 27.2, rounded up to 28 — not a plain sum of 48.
    assert saved.json()["data"]["totals"][0] == 28
    # The exam link is derived server-side even when the client omits it, so
    # result processing can match internal marks to the examination.
    assert assignment["examination_id"]
    with SessionLocal() as db:
        mark = db.query(InternalMark).filter_by(
            student_id=uuid.UUID(student["id"]), subject_id=uuid.UUID(assignment["subject_id"])
        ).first()
        assert mark is not None
        assert str(mark.examination_id) == assignment["examination_id"]


def test_marks_draft_then_submit_and_locked_protection(client, faculty_headers, admin_headers):
    assignment, student = _assignment_and_student(client, faculty_headers)
    payload = _marks_payload(assignment["subject_id"], student["id"])
    saved = client.post("/api/v1/faculty/me/internal-marks", json=payload, headers=faculty_headers)
    assert saved.status_code == 200, saved.text
    submitted = client.post("/api/v1/faculty/me/marks-submissions", json=payload, headers=faculty_headers)
    assert submitted.status_code == 200, submitted.text
    submission_id = submitted.json()["data"]["id"]
    locked = client.post(
        f"/api/v1/admin/marks-verification/{submission_id}?action=lock", headers=admin_headers
    )
    assert locked.status_code == 200, locked.text
    second_attempt = client.post("/api/v1/faculty/me/internal-marks", json=payload, headers=faculty_headers)
    assert second_attempt.status_code == 409


def test_faculty_cannot_enter_marks_for_unassigned_subject(client, faculty_headers):
    response = client.post(
        "/api/v1/faculty/me/internal-marks",
        json={"subject_id": str(uuid.uuid4()), "entries": []},
        headers=faculty_headers,
    )
    assert response.status_code == 403
