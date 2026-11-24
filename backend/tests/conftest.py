"""Pytest fixtures: fresh seeded SQLite database for every test."""
from __future__ import annotations

import os

os.environ["DATABASE_URL"] = "sqlite:///./pytest_exam.db"
os.environ["ENVIRONMENT"] = "testing"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.models  # noqa: F401,E402
from app.database.seed import seed_test_db  # noqa: E402
from app.database.session import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_test_db(db)
    yield


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def login(client: TestClient, email: str, password: str) -> dict:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


@pytest.fixture
def admin_headers(client: TestClient) -> dict:
    return login(client, "admin@example.com", "Admin@123")


@pytest.fixture
def faculty_headers(client: TestClient) -> dict:
    return login(client, "faculty@example.com", "Faculty@123")


@pytest.fixture
def student_headers(client: TestClient) -> dict:
    return login(client, "student@example.com", "Student@123")


@pytest.fixture
def student2_headers(client: TestClient) -> dict:
    return login(client, "student2@example.com", "Student@123")
