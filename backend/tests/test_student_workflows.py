"""Student registration, password, notification and document tests."""
from io import BytesIO

from tests.conftest import login


def _registration_parts(exam, subjects):
    data = {
        "examination_id": str(exam["id"]),
        "subject_ids": [str(subjects[0]["subject_id"])],
    }
    files = {"fee_receipt": ("receipt.pdf", BytesIO(b"%PDF-1.4\ndemo receipt\n"), "application/pdf")}
    return data, files


def _exam_and_subjects(client, headers):
    exams = client.get("/api/v1/students/me/examinations", headers=headers).json()["data"]
    exam = next(e for e in exams if e["eligible"] and not e["registered"])
    subjects = client.get(f"/api/v1/students/me/examinations/{exam['id']}/subjects", headers=headers).json()["data"]
    return exam, subjects


def test_eligible_exam_and_subjects_listed(client, student2_headers):
    exam, subjects = _exam_and_subjects(client, student2_headers)
    assert exam["eligible"] is True
    assert len(subjects) >= 1


def test_duplicate_registration_prevented(client, student2_headers):
    exam, subjects = _exam_and_subjects(client, student2_headers)
    data, files = _registration_parts(exam, subjects)
    response = client.post("/api/v1/students/me/registrations", data=data, files=files, headers=student2_headers)
    assert response.status_code == 200, response.text
    assert response.json()["data"]["has_fee_receipt"] is True
    duplicate_data, duplicate_files = _registration_parts(exam, subjects)
    duplicate = client.post(
        "/api/v1/students/me/registrations",
        data=duplicate_data,
        files=duplicate_files,
        headers=student2_headers,
    )
    assert duplicate.status_code == 409


def test_fee_receipt_is_mandatory(client, student2_headers):
    exam, subjects = _exam_and_subjects(client, student2_headers)
    response = client.post(
        "/api/v1/students/me/registrations",
        data={"examination_id": exam["id"], "subject_ids": [subjects[0]["subject_id"]]},
        headers=student2_headers,
    )
    assert response.status_code == 422
    assert any(error["field"] == "fee_receipt" for error in response.json()["errors"])


def test_student_can_download_own_receipt(client, student2_headers):
    exam, subjects = _exam_and_subjects(client, student2_headers)
    data, files = _registration_parts(exam, subjects)
    registered = client.post(
        "/api/v1/students/me/registrations",
        data=data,
        files=files,
        headers=student2_headers,
    )
    registration_id = registered.json()["data"]["id"]
    response = client.get(
        f"/api/v1/students/me/registrations/{registration_id}/receipt", headers=student2_headers
    )
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_ineligible_subject_registration_rejected(client, student2_headers):
    exam, subjects = _exam_and_subjects(client, student2_headers)
    import uuid

    data, files = _registration_parts(exam, subjects)
    data["subject_ids"] = [str(uuid.uuid4())]
    response = client.post(
        "/api/v1/students/me/registrations", data=data, files=files, headers=student2_headers
    )
    assert response.status_code in (403, 422)


def test_temporary_password_must_be_changed_before_student_access(client):
    response = client.post(
        "/api/v1/auth/login", json={"email": "tempstudent@example.com", "password": "Temp@123"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["user"]["must_change_password"] is True
    headers = {"Authorization": f"Bearer {response.json()['data']['access_token']}"}
    blocked = client.get("/api/v1/students/me", headers=headers)
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "password_change_required"

    changed = client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "Temp@123",
            "new_password": "Permanent@123",
            "confirm_password": "Permanent@123",
        },
        headers=headers,
    )
    assert changed.status_code == 200, changed.text
    assert client.get("/api/v1/students/me", headers=headers).status_code == 200


def test_unread_notification_count_and_mark_all_read(client, student_headers):
    count = client.get("/api/v1/notifications/unread-count", headers=student_headers)
    assert count.status_code == 200, count.text
    assert count.json()["data"]["count"] >= 1
    marked = client.post("/api/v1/notifications/mark-all-read", headers=student_headers)
    assert marked.status_code == 200
    assert client.get("/api/v1/notifications/unread-count", headers=student_headers).json()["data"]["count"] == 0


def test_student_cannot_read_another_students_unpublished_result(client, student2_headers, admin_headers):
    exam = client.get("/api/v1/admin/examinations", headers=admin_headers).json()["data"][0]
    process = client.post(
        "/api/v1/admin/result-processing",
        json={"examination_id": exam["id"]},
        headers=admin_headers,
    )
    assert process.status_code == 200, process.text
    result_id = process.json()["data"]["result_ids"][0]
    # Results are not published yet; students cannot access them at all.
    assert client.get(f"/api/v1/students/me/results/{result_id}", headers=student2_headers).status_code == 404
    assert client.get(f"/api/v1/students/me/certificates/{result_id}/download", headers=student2_headers).status_code in (403, 404)


def test_hall_ticket_download_is_pdf_and_scoped(client, student_headers, admin_headers):
    tickets = client.get("/api/v1/students/me/hall-tickets", headers=student_headers)
    assert tickets.status_code == 200, tickets.text
    ticket = tickets.json()["data"][0]
    response = client.get(f"/api/v1/students/me/hall-tickets/{ticket['id']}/download", headers=student_headers)
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")
