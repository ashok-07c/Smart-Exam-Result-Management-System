# JNTUA College Of Engineering Pulivendula Smart Exam Result Management System

A self-contained full-stack application for examination registration, SBI Collect fee receipts, fixed-format internal marks, central grading, result processing, SGPA/CGPA, backlogs, recounting, notifications and branded document generation.

> The surrounding workspace contains unrelated tutorial projects. Everything for this system lives inside `smart-exam-system/`; no root-level tutorial files were modified.

## Contents

- `backend/` — FastAPI + SQLAlchemy + PostgreSQL (SQLite for local verification), Alembic migrations, pytest suite, PDF generation.
- `frontend/` — React 18 + TypeScript + Vite, React Router, TanStack Query, React Hook Form, Zod, Recharts, Tailwind CSS and shadcn-style components.
- `docs/` — architecture, API contract, verification record, update checklist and final implementation report.
- `docker-compose.yml` — PostgreSQL + backend + frontend stack.

## Roles

Exactly three roles are supported: `STUDENT`, `FACULTY`, `EXAM_ADMIN`. The role is always read from the database on every request; the client cannot grant or change it.

| Portal | Capabilities |
| --- | --- |
| Student | Mandatory password change for temporary accounts, eligibility, exam registration with SBI Collect receipt upload/download, timetable, hall tickets, MID-1/MID-2/Assignments marks, numeric correction requests, published results, SGPA/CGPA chart, backlogs, recounting requests, unread notification badges. |
| Faculty | Full-name greeting, assigned subjects/classes, students, fixed-component marks entry with authoritative total preview, submissions, numeric correction review, timetable, unread notification badges. |
| Exam Admin | Six-course academic records (CSE, ECE, EEE, MECH, CIVIL, AI&ML), years from 2023, exam configuration, registrations and receipt download, schedules/timetable, hall tickets, marks verification/management, two-phase CSV external-mark import, central result processing, approval/publication, SGPA/CGPA overview, backlogs, recounting, notification publishing, password reset. Reports/Exports and Audit Log tabs were removed from the UI. |

## Quick start (Docker)

```bash
cd smart-exam-system
cp backend/.env.example backend/.env       # optional: compose supplies safe local defaults
docker compose up --build
```

- Frontend: http://localhost:8080
- Backend: http://localhost:8000
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

Compose runs `alembic upgrade head` before starting the API and supplies the exact `APP_NAME`. Set `SECRET_KEY`, `POSTGRES_PASSWORD` and CORS origins through environment variables or a root `.env` before any non-local use.

## Quick start (local, no Docker)

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env               # set DATABASE_URL=sqlite:///./exam.db for a local file DB
alembic upgrade head
python -m app.database.seed --credentials-out ./institution_credentials.csv
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
copy .env.example .env.local         # VITE_API_BASE_URL=http://localhost:8000/api/v1
npm run dev                          # http://localhost:5173
```

## Institution seed data

`python -m app.database.seed` loads the supplied institution data from `backend/app/data/`: **30 faculty, 30 subjects and 100 students** across CSE, ECE, EEE, MECH and CIVIL. Each subject has exactly one teacher from its own department. `AI&ML` remains a selectable course, but no records are invented because none were supplied.

The seed uses simple, predictable initial passwords of the form `name@123` (titles removed, spaces replaced with dots), so `admin@123` is the exam-admin password, `Dr. Suresh Babu` is `suresh.babu@123`, and `Arjun Kumar` is `arjun.kumar@123`. Duplicate names share the same password; the unique email is the login identifier. It writes every email/password pair to the path passed to `--credentials-out`. These are local-seed credentials only; rotate them before deployment. All seeded students have `must_change_password = true`, so the first login routes them to the change-password screen.

Use a fresh migrated database. The seed deliberately refuses to run when users already exist, so demo data cannot be mixed with institution data. The old demo accounts (`admin@example.com`, `faculty@example.com`, `student@example.com`, etc.) are **not** created by the default seed and no longer appear on the login screen. They exist only in the isolated pytest fixture (`python -m app.database.seed --test-data`) and are never used by the running app.

## Important behaviour

- All API responses use `{ success, message, data, errors?, code? }`. Paginated `data` uses `{ items, total, page, page_size, pages }`.
- JWT access token is kept client-side; refresh token is an HttpOnly cookie scoped to `/api/v1/auth`.
- The frontend never computes grades, pass/fail, eligibility or stored totals. It renders server decisions only.
- Grading is central and fixed in `app/services/grading.py`: `S > 90`, `A > 80`, `B ≥ 70`, `C > 60`, `D > 50`, `E ≥ 40`, `Fail < 40`. Overall percentage ≥ 40 passes; exactly 40 is a passing `E`.
- Internal assessment is fixed: MID-1/25, MID-2/25, Assignments/5; total is `(best × 0.8) + (other × 0.2) + assignments`, rounded half-up to two decimals.
- Fee receipts are validated, stored privately and served only through authenticated student/admin endpoints. No public upload path exists.
- External-mark CSV imports are two-phase: validate/preview into a DB staging row, then explicit confirm. Results are never auto-published.
- `VITE_API_MODE=mock` enables an explicitly labelled demo adapter mirrored to the new contracts. Live API failures are never silently replaced with mock data.
- Result publication is an explicit workflow: process → approve → publish.

## Verification

```bash
# Backend
cd backend && .venv/Scripts/python -m pytest -q

# Frontend
cd frontend && npm run typecheck && npm run lint && npm run build
```

Latest results and honest limitations are in [`docs/IMPLEMENTATION_PROGRESS.md`](docs/IMPLEMENTATION_PROGRESS.md). The requirement-by-requirement mapping is in [`docs/FINAL_IMPLEMENTATION_REPORT.md`](docs/FINAL_IMPLEMENTATION_REPORT.md).
