# Architecture — JNTUA College Of Engineering Pulivendula Smart Exam Result Management System

## System shape

```
Browser (React SPA)
   │  HTTPS / JSON, Bearer access token + HttpOnly refresh cookie
   ▼
FastAPI application  ──►  PostgreSQL (authoritative data in deployment)
   │                        ▲
   │                        └── Alembic migrations
   ├── services/grading.py          central grade/pass/SGPA/CGPA authority
   ├── services/internal_marks.py   fixed MID-1 / MID-2 / Assignments formula
   ├── services/audit.py            audit trail for sensitive operations
   ├── services/notifications.py    recipient-scoped in-app notifications
   ├── utils/uploads.py             validated private fee-receipt storage
   └── utils/pdf.py                 hall tickets, timetables, result certificates
```

The **backend is authoritative** for identity, role, temporary-password enforcement, eligibility, marks acceptance, grade/pass decisions, SGPA/CGPA, backlog derivation, recounting state, fee receipts, CSV import staging and result publication. The SPA only renders server decisions and posts user intent.

The exact product heading is `JNTUA College Of Engineering Pulivendula Smart Exam Result Management System`. It appears in the browser title/metadata, the login layout, the sidebar branding, the backend `APP_NAME`, `.env.example` and the Compose defaults. Generated hall tickets and result certificates print `JNTUA College Of Engineering Pulivendula` from `settings.institution_name`.

## Roles

Exactly three roles exist, stored in `users.role`:

| Role | Scope |
| --- | --- |
| `STUDENT` | Own profile, registrations with fee receipts, timetable, hall tickets, marks, numeric corrections, results, backlogs, recounting requests, notifications. |
| `FACULTY` | Assigned subjects/classes only; fixed-component marks entry, drafts, submissions, numeric correction review, timetable, notifications. |
| `EXAM_ADMIN` | Six-course academic records, years from 2023, examinations, registrations/receipts, schedules, hall tickets, marks verification/management, CSV imports, result processing, approval/publication, SGPA/CGPA, backlogs, recounting, notification publishing, password reset. |

There is no Super Admin or Root Admin. `deps.py` resolves the `User` row from the access-token subject on each request, checks `account_status` and role, and gates endpoints with `CurrentStudent`, `CurrentFaculty` or `ExamAdmin`. Faculty subject access is additionally checked against `FacultyAssignment`. A student with `users.must_change_password = true` is rejected by `get_current_student` with `403 password_change_required` on every student workflow until `POST /auth/change-password` succeeds.

## Backend layers

1. **Routers** (`app/api/v1/endpoints`) — thin, validate via Pydantic, call services, return the standard envelope. Grouped into auth, student, faculty, shared notifications, and three admin modules (records, exams, academic). The app exposes **92 OpenAPI paths total: 91 under `/api/v1` plus `/health`**.
2. **Dependencies** (`app/core/deps.py`) — authentication, role checks, temporary-password gate, DB session, pagination bounds.
3. **Models** (`app/models`) — **35 SQLAlchemy tables**, covering users, academics, examinations, marks, results, imports, receipts references, notifications and audit. Enums are centralised in `enums.py`.
4. **Services** — pure domain logic reused across endpoints:
   - `grading.GradeConfig` — fixed S/A/B/C/D/E/Fail bands, 40% pass rule, half-up rounding, credit-weighted SGPA/CGPA. Regulation JSON is deliberately ignored.
   - `internal_marks` — fixed components and authoritative total; rejects non-numeric/out-of-range values.
   - `audit.log()` — actor, action, entity, previous/new values and timestamp.
   - `notifications` — recipient-scoped messages; unread count is served from `NotificationRecipient.read_at`.
   - `uploads` — receipt validation, random private filenames, path-traversal protection and cleanup on failed transactions.
5. **Infrastructure** — `config.Settings` (environment, branding, upload directory), `security` (bcrypt/JWT), `responses` (envelope/pagination), `exceptions` (single error handler), `database.session` (engine/session), `utils.pdf` (documents).

## Data flow: the critical paths

### Registration with fee receipt
1. Student checks server-evaluated eligible examinations and subjects.
2. Student submits `multipart/form-data`: `examination_id`, repeated `subject_ids`, and a `fee_receipt` (PDF/JPG/PNG, ≤ 5 MB).
3. Backend validates the file, exam window, branch/semester/backlog eligibility, subject scope and duplicates.
4. Receipt is saved under a random name in `UPLOAD_DIR/fee_receipts`; DB row stores only the relative path, original filename, content type and upload timestamp.
5. Registration and subject rows are written in one transaction with audit events. On failure the DB rolls back and the new file is removed.
6. Student and admin download the receipt through authenticated binary endpoints; no public/static path is exposed.

### Internal marks
1. Faculty see exactly MID-1/25, MID-2/25 and Assignments/5 for assigned subjects only.
2. The UI previews `(best × 0.8) + (other × 0.2) + assignments` but never sends a total.
3. Backend validates each component, rounds the total up to the next whole mark (e.g. `27.2 → 28`), stores numeric columns and a readable `component_marks` snapshot, and refuses edits once submitted/verified/locked. Subjects are internal 30 / external 70.
4. Numeric correction requests use `subject_code`, `reported_marks`, `suggested_marks` and `explanation` — no JSON fields. Faculty `correct` actions write numeric corrected marks and return the affected internal mark to `IN_PROGRESS` unless locked.

### External marks CSV import
1. Admin downloads a template (`rollno,subcode,marks`) and uploads a UTF-8 CSV against a chosen examination.
2. Backend validates headers, size (≤ 5 MB), row count (≤ 10,000), roll numbers, subject codes, numeric range and duplicates, then stores a DB-backed `ExternalMarkImport` with `status=PENDING` and per-row diagnostics. **No marks are written in this phase.**
3. UI renders the staged preview with per-row status/errors and a summary.
4. Explicit confirmation applies valid rows in one transaction. By default existing marks are skipped; `overwrite=true` updates them. Both phases write audit rows. Nothing is processed or published automatically.

### Result processing, publication and recounting
1. Admin configures academic years (2023 onward), the six supported course codes, subjects and regulation labels. Regulation JSON no longer carries grading/pass rules.
2. Result processing requires verified/locked internal marks and external marks for each registered subject.
3. The server computes each total, applies the central grade/pass rules, derives SGPA/CGPA, creates/updates `SemesterResult` + `SubjectResult` rows at `READY_FOR_REVIEW`, and updates backlog state — all transactionally.
4. Publication is a separate state machine: `READY_FOR_REVIEW → APPROVED → PUBLISHED`, with `unpublish` returning to `APPROVED`. Only `PUBLISHED` results are visible to students.
5. Recounting can only be requested against a published result (default 30-day window from publication, optionally overridden by examination criteria). It stores original marks, status history and notifications. Admin processing validates revised totals against component maxima, recomputes grade/pass/SGPA/CGPA/backlogs, and returns the result to `READY_FOR_REVIEW` for re-approval.

## Frontend structure

```
src/
  main.tsx                  providers + router + Toaster
  App.tsx                   route table with role guards and temp-password redirect
  providers/                QueryProvider, AuthProvider, auth-context
  routes/ProtectedRoute.tsx role gate, guest gate, change-password gate
  components/ui/            shadcn-style primitives (Card, DataTable, Modal, Field, …)
  components/layout/AppShell.tsx  exact branding, role nav, unread badges, full name
  features/auth/            login, change password, forgot/reset password, unauthorized
  features/student/pages/   12 student pages (registration receipt + numeric corrections)
  features/faculty/pages.tsx 9 faculty pages (fixed marks grid + numeric corrections)
  features/admin/pages.tsx  17 admin pages (no Reports or Audit Log)
  features/common/          notifications inbox
  lib/                      api client, mock adapter, hooks, types, utils, roles
```

- **State/data:** TanStack Query owns server state. `useApiQuery` reads `{success,message,data}` envelopes; `useApiEnvelope` is used where pagination metadata lives inside `data`. Mutations call `api` and invalidate queries on success.
- **Auth UX:** `AuthUser.must_change_password` drives `RootRedirect`, `ProtectedRoute` and `PasswordChangeRoute`. The account menu and greeting use the backend `full_name`, not a hardcoded name. The login page has no local/demo-accounts panel; credentials come only from the institution seed.
- **Badges:** `AppShell` fetches `/notifications/unread-count` and shows counts in both the sidebar and header; read actions invalidate the count query.
- **Forms:** React Hook Form + Zod in auth and mark-entry flows; other forms use controlled inputs with server-side validation as the real authority.
- **Charts:** Recharts render SGPA/CGPA trends from server-provided series.
- **Styling:** Tailwind CSS with CSS variables and shadcn-style components; responsive layouts checked at 360, 390, 768, 1024 and 1440 px.
- **API mode:** `VITE_API_MODE=live` (default) talks to the real backend. `VITE_API_MODE=mock` opts into a clearly labelled demo adapter that now mirrors the new auth, receipt, numeric correction, external-mark and CSV contracts. A failed live request surfaces an error — it is never silently swapped for mock data.

## Auth flow

1. `POST /auth/login` returns an access token plus a user object containing `full_name`, `role` and `must_change_password`; it sets a refresh cookie scoped to `/api/v1/auth`.
2. The SPA keeps the access token client-side and sends it as `Authorization: Bearer …`.
3. On 401, the API client calls `POST /auth/refresh` once (single-flight), then retries the original request. If refresh fails, it clears local auth and redirects to login.
4. If `must_change_password` is true, the SPA routes to `/change-password` and the backend blocks other student endpoints. After success the flag is cleared in DB and the returned user is updated in the client.
5. Role for routing comes from the backend user object; the backend re-validates the role from the DB on every protected request.

## Database & migrations

- PostgreSQL is the deployment target; SQLite is used for local verification and tests.
- Alembic chain:
  - `719c140e49c8_initial_schema.py` — initial 34-table schema.
  - `0f3a7b2c9d41_workflow_updates.py` — adds `must_change_password`, fee-receipt columns, numeric internal/correction/result columns, internal FKs, `external_mark_imports`, and migrates legacy component/mark JSON to the new fixed structure. Downgrade is implemented.
- Migration upgrade → downgrade → upgrade was smoke-tested on a disposable SQLite database.
- `python -m app.database.seed` loads the supplied institution CSVs (`backend/app/data/`): 30 faculty, 30 subjects, 100 students and 30 faculty assignments, each teacher belonging to the subject's department. It also creates the 2023-24/2024-25/2025-26 years, eight semesters, the six selectable courses and the fixed internal-mark component definition. No exams, marks, registrations or notifications are fabricated.
- Initial credentials use the simple local-seed pattern `name@123` (admin is `admin@123`; titles removed and spaces replaced with dots), are bcrypt-hashed and written to `--credentials-out`. Seeded students start with `must_change_password = true`. The seed refuses to run on a non-empty database. These passwords must be rotated before deployment.
- The former demo dataset is isolated in `seed_test_db()`, called only by pytest and by `--test-data`; the login screen no longer renders a local-accounts panel.

## Deployment

`docker-compose.yml` starts PostgreSQL, the backend (runs `alembic upgrade head` then Uvicorn) and the frontend (Vite build served by nginx with SPA fallback). It also supplies the exact `APP_NAME`. See `../README.md` and `../backend/README.md`.

## Verification summary

- Backend: **47 pytest tests passed** (one upstream `StarletteDeprecationWarning`).
- Frontend: `npm run typecheck`, `npm run lint` and `npm run build` pass.
- OpenAPI: **92 paths**; SQLAlchemy metadata: **35 tables**.
- PostgreSQL/Docker containers were not run locally because no daemon is available; all functional verification used SQLite.
