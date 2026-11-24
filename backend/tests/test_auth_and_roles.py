"""Authentication and role-boundary tests."""
from tests.conftest import login


def test_valid_login_returns_role_from_database(client):
    for email, expected_role in [
        ("admin@example.com", "EXAM_ADMIN"),
        ("faculty@example.com", "FACULTY"),
        ("student@example.com", "STUDENT"),
    ]:
        response = client.post("/api/v1/auth/login", json={"email": email, "password": "Admin@123" if "admin" in email else ("Faculty@123" if "faculty" in email else "Student@123")})
        assert response.status_code == 200, response.text
        assert response.json()["data"]["user"]["role"] == expected_role


def test_invalid_password_rejected(client):
    response = client.post("/api/v1/auth/login", json={"email": "student@example.com", "password": "WrongPassword1!"})
    assert response.status_code == 401
    assert response.json()["success"] is False


def test_role_cannot_access_other_portal(client, student_headers, faculty_headers, admin_headers):
    paths = [
        ("/api/v1/admin/students", student_headers),
        ("/api/v1/faculty/me/assignments", student_headers),
        ("/api/v1/students/me/results", faculty_headers),
        ("/api/v1/admin/dashboard", faculty_headers),
        ("/api/v1/faculty/me/internal-marks", admin_headers),
    ]
    for path, headers in paths:
        response = client.get(path, headers=headers)
        assert response.status_code == 403, (path, response.text)


def test_me_and_refresh_cookie(client):
    response = client.post("/api/v1/auth/login", json={"email": "student@example.com", "password": "Student@123"})
    assert "exam_refresh_token" in response.cookies
    refresh = client.post("/api/v1/auth/refresh")
    assert refresh.status_code == 200, refresh.text
    assert refresh.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {refresh.json()['data']['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200


def test_expired_or_invalid_token_rejected(client):
    response = client.get("/api/v1/students/me", headers={"Authorization": "Bearer not.a.token"})
    assert response.status_code == 401
