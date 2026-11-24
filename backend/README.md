# Backend — JNTUA College Of Engineering Pulivendula Smart Exam Result Management System

FastAPI service that is the single source of truth for authentication, temporary-password enforcement, roles, eligibility, fee receipts, marks, central grading, SGPA/CGPA, backlogs, recounting, CSV imports and result publication. The frontend never performs these decisions itself.

## Stack

- FastAPI 0.115+ / Uvicorn
- SQLAlchemy 2.x with Alembic migrations (35 tables, four revisions)
- PostgreSQL (`psycopg[binary]`) in deployment; SQLite supported for local verification and tests
- Pydantic v2 settings & request schemas
- PyJWT + bcrypt for authentication
- ReportLab (hall tickets, timetable, certificates)
- pytest + httpx for the test suite

## Layout

```
app/
  main.py                  FastAPI app, CORS, exception handlers, /health, router mount
  core/
    config.py              env-driven Settings, exact institution/app branding, upload dir
    security.py            bcrypt hashing, access/refresh JWT creation and validation
    deps.py                auth, role and temporary-password gates, assignment checks, pagination
    exceptions.py          ApiError hierarchy + single error-envelope handler
    responses.py           ok() envelope and generic Page[T]
  database/
    session.py             engine, SessionLocal, get_db, Base
    seed.py                institution seed (app/data CSVs) + isolated pytest fixture seed
  data/                   supplied faculty, subject and student CSV data
  models/                  SQLAlchemy models (35 tables) and enums
  schemas/                 Pydantic request/response models
  services/
    grading.py             central grade/pass/SGPA/CGPA engine (regulation JSON ignored)
    internal_marks.py      fixed MID-1/MID-2/Assignments validation and authoritative total
    audit.py               audit-log writer for sensitive operations
    notifications.py       recipient-scoped in-app notification writer
  utils/
    uploads.py             validated private fee-receipt storage
    pdf.py                 PDF document helpers (institution name from settings)
  api/v1/
    router.py              aggregates all v1 endpoint routers
    endpoints/             auth, student, faculty, notifications, admin_records,
                           admin_exams, admin_academic
  migrations/versions/     719c140e49c8 (initial) + 0f3a7b2c9d41 + b1c2d3e4f5a6 + c2d3e4f5a6b7
tests/                     55 tests across auth/roles and the three role workflows
```

## Setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

- `DATABASE_URL` — `postgresql+psycopg://exam:exam@localhost:5432/exam` for Postgres, or `sqlite:///./exam.db` locally.
- `SECRET_KEY` — long random value; the default is development-only.
- `CORS_ORIGINS` — comma-separated frontend origins, no trailing slash.
- `REFRESH_COOKIE_SECURE=true` when serving over HTTPS; keep `lax`/`strict` SameSite.
- `APP_NAME` — exact product heading; `INSTITUTION_NAME`/`INSTITUTION_ADDRESS` — identity printed on PDFs.
- `UPLOAD_DIR` — private directory for fee receipts (default `./uploads`). It is not served statically.

## Run

```bash
alembic upgrade head
python -m app.database.seed --credentials-out ./institution_credentials.csv
uvicorn app.main:app --reload --port 8000
```

The default seed loads `app/data/faculty.csv`, `app/data/subjects.csv` and
`app/data/students.csv` into a **fresh** database: 30 faculty, 30 subjects,
100 students and 30 department-scoped `FacultyAssignment` rows. It refuses to
run when users already exist so demo data cannot be mixed with institution
data. Initial passwords follow `name@123` (admin is `admin@123`; titles are
removed and spaces become dots for other names) and are written to
`--credentials-out` (or printed when the flag is omitted). These are simple
local-seed credentials, not production secrets. `SEED_ADMIN_EMAIL`,
`SEED_FACULTY_DOMAIN` and `SEED_STUDENT_DOMAIN` override the account domains.

The small demo dataset needed by the test suite is seeded only by
`python -m app.database.seed --test-data` and by `tests/conftest.py`; it is
never used by the running app.

- API docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`
- All business endpoints are under `/api/v1` (91 paths); `/health` is the only unversioned OpenAPI path, for 92 total.

For SQLite local use, Alembic is optional: the app creates tables at startup. PostgreSQL deployments must run `alembic upgrade head` (Compose does this automatically).

## Tests

```bash
.venv/Scripts/python -m pytest -q
```

The isolated SQLite suite covers login/role enforcement, temporary-password gating, registration with receipts, fixed internal marks and totals, numeric corrections, central grading boundaries, the six courses/years-from-2023 seed, enriched external marks, CSV preview/confirm/audit, result processing/publication, recounting revision, and authorization boundaries.

## Security notes

- Passwords are bcrypt-hashed; plaintext is never stored. Institution-seed passwords are deterministic `name@123` values (admin: `admin@123`) written to `--credentials-out`; change them before deployment.
- `users.must_change_password` is persisted and checked in `get_current_student`; changing the password verifies the current one, enforces complexity and clears the flag in one transaction.
- Access tokens are short-lived JWTs. The refresh token is an HttpOnly cookie scoped to `/api/v1/auth`.
- The role is read from the user row on **every** request, never from the client or token body.
- Faculty endpoints verify the requested subject/section against `FacultyAssignment` rows before returning or accepting data.
- Fee receipts are restricted to PDF/JPG/PNG and 5 MB, saved with random filenames under `UPLOAD_DIR`, path-checked on download, and deleted if the surrounding DB transaction fails. Only the owning student or an exam admin can download them.
- CSV imports are size/row bounded, validated before writing, staged in `external_mark_imports`, and applied only on explicit confirmation. Audit rows record both phases.
- Sensitive operations write audit-log rows. Academic mutations use database transactions so partial results are rolled back on failure.
- Grades, pass/fail and stored totals are central server decisions. Regulation JSON no longer influences results.
