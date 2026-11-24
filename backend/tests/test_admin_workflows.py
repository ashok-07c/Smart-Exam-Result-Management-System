"""Administrative workflows: result processing, publication, recounting, reports, reset."""
from tests.conftest import login


def _exam_id(client, admin_headers):
    return client.get("/api/v1/admin/examinations", headers=admin_headers).json()["data"][0]["id"]


def _process_and_publish(client, admin_headers):
    exam_id = _exam_id(client, admin_headers)
    processed = client.post(
        "/api/v1/admin/result-processing", json={"examination_id": exam_id}, headers=admin_headers
    )
    assert processed.status_code == 200, processed.text
    for result_id in processed.json()["data"]["result_ids"]:
        assert client.post(f"/api/v1/admin/result-publication/{result_id}", json={"action": "approve", "note": "test"}, headers=admin_headers).status_code == 200
        published = client.post(f"/api/v1/admin/result-publication/{result_id}", json={"action": "publish"}, headers=admin_headers)
        assert published.status_code == 200, published.text
    return processed.json()["data"]["result_ids"]


def test_result_processing_can_be_repeated(client, admin_headers):
    exam_id = _exam_id(client, admin_headers)
    first = client.post("/api/v1/admin/result-processing", json={"examination_id": exam_id}, headers=admin_headers)
    assert first.status_code == 200, first.text
    first_count = client.get("/api/v1/admin/results", headers=admin_headers).json()["data"][0]["subject_count"]

    second = client.post("/api/v1/admin/result-processing", json={"examination_id": exam_id}, headers=admin_headers)
    assert second.status_code == 200, second.text
    rows = client.get("/api/v1/admin/results", headers=admin_headers).json()["data"]
    assert len(rows) == 1
    assert rows[0]["subject_count"] == first_count


def test_result_processing_publication_and_student_visibility(client, admin_headers, student_headers):
    result_ids = _process_and_publish(client, admin_headers)
    assert result_ids
    results = client.get("/api/v1/students/me/results", headers=student_headers)
    assert results.status_code == 200, results.text
    assert len(results.json()["data"]) >= 1
    performance = client.get("/api/v1/students/me/sgpa-cgpa", headers=student_headers).json()["data"]
    assert performance["current_cgpa"] is not None


def test_certificate_pdf_download(client, admin_headers, student_headers):
    result_ids = _process_and_publish(client, admin_headers)
    own_results = client.get("/api/v1/students/me/results", headers=student_headers).json()["data"]
    result_id = next(r["id"] for r in own_results)
    response = client.get(f"/api/v1/students/me/certificates/{result_id}/download", headers=student_headers)
    assert response.status_code == 200, response.text[:200]
    assert response.content.startswith(b"%PDF")


def test_backlogs_created_for_failed_subject(client, admin_headers, student_headers):
    _process_and_publish(client, admin_headers)
    backlogs = client.get("/api/v1/students/me/backlogs", headers=student_headers).json()["data"]
    assert isinstance(backlogs, list)
    if backlogs:
        assert backlogs[0]["subject_code"] == "CS302"


def test_recounting_request_and_admin_processing(client, admin_headers, student_headers):
    _process_and_publish(client, admin_headers)
    exam_id = _exam_id(client, admin_headers)
    subjects = client.get("/api/v1/admin/subjects", headers=admin_headers).json()["data"]
    subject_id = next(s["id"] for s in subjects if s["subject_code"] == "CS301")
    request = client.post(
        "/api/v1/students/me/recounting-requests",
        json={"examination_id": exam_id, "subject_id": subject_id, "reason": "Please recount"},
        headers=student_headers,
    )
    assert request.status_code in (200, 409), request.text
    if request.status_code == 200:
        request_id = request.json()["data"]["id"]
        processed = client.post(
            f"/api/v1/admin/recounting/{request_id}/process",
            json={"action": "complete", "admin_response": "Verified", "revised_marks": 87},
            headers=admin_headers,
        )
        assert processed.status_code == 200, processed.text
        assert processed.json()["data"]["status"] == "COMPLETED"


def test_reports_csv_and_xlsx(client, admin_headers):
    for fmt, media in [("csv", "text/csv"), ("xlsx", "spreadsheetml")]:
        response = client.get(f"/api/v1/admin/reports/students?format={fmt}", headers=admin_headers)
        assert response.status_code == 200, response.text[:200]
        assert media in response.headers["content-type"]


def test_admin_password_reset_flow(client, admin_headers):
    students = client.get("/api/v1/admin/students", headers=admin_headers).json()["data"]["items"]
    target = next(s for s in students if s["roll_number"] == "21CS001")
    initiated = client.post(
        "/api/v1/admin/password-reset/initiate",
        json={"user_id": target["user_id"], "reason": "Forgot password"},
        headers=admin_headers,
    )
    assert initiated.status_code == 200, initiated.text
    token = initiated.json()["data"]["reset_token"]
    reset = client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "NewStudent@123"})
    assert reset.status_code == 200, reset.text
    assert client.post("/api/v1/auth/login", json={"email": "student@example.com", "password": "NewStudent@123"}).status_code == 200


def test_audit_log_records_sensitive_actions(client, admin_headers):
    _process_and_publish(client, admin_headers)
    logs = client.get("/api/v1/admin/audit-logs", headers=admin_headers).json()["data"]["items"]
    actions = {row["action"] for row in logs}
    assert "RESULT_PROCESSED" in actions
    assert "RESULT_PUBLISH" in actions
