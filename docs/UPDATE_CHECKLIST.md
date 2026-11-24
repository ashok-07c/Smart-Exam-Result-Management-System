# Update Progress Checklist

Tracks the requested update. Status values: `pending`, `in progress`, `done`, `blocked`.

## 0. Inspection & planning
- [x] Inspect project structure, stack, schema, endpoints, auth/RBAC, three role portals — 2026-11-23
- [x] Identify bugs for each requested change — stale branding, JSON-driven grading, non-mandatory receipt, JSON correction fields, non-functional recounting, missing badges, hardcoded faculty name, missing CSV workflow, extra admin tabs
- [x] Write implementation plan + checklist

## 1. General
- [x] Exact heading `JNTUA College Of Engineering Pulivendula Smart Exam Result Management System` in login layout, sidebar/dashboard branding, browser title, HTML metadata, backend `APP_NAME`, `.env.example` and Compose defaults
- [x] Institution `JNTUA College Of Engineering Pulivendula` on hall-ticket and result-certificate PDFs via `settings.institution_name`

## 2. Student
- [x] 3.1 `users.must_change_password` persisted; `/auth/change-password` + guarded route/page; backend blocks student workflows until cleared; institution-seeded students start with the flag set, and the former demo account is test-fixture-only
- [x] 3.2 Mandatory `SBI Collect Fee Payment Receipt` multipart upload, type/size validation, private random-name storage, DB reference, student and admin authenticated download, UI download actions
- [x] 3.3 Institution name on hall ticket + result certificate PDFs
- [x] 3.4 Marks correction now uses text `subject_code` + numeric `reported_marks`/`suggested_marks` + `explanation`; JSON fields removed from model/schema/migration/UI
- [x] 3.5 Central grading S/A/B/C/D/E/Fail in `app/services/grading.py`; backend authoritative; frontend displays server grade; exact boundaries documented and unit-tested
- [x] 3.6 Recounting workflow end-to-end: requires published result, 30-day default window, subject membership check, status history, admin validation/revision, grade/pass/SGPA/CGPA/backlog recomputation, notifications
- [x] 3.7 Student sidebar + header unread notification badge from `GET /notifications/unread-count`, invalidated on read actions

## 3. Faculty
- [x] 4.1 Full faculty name from DB/API in greeting, account menu and profile; no hardcoded display name
- [x] 4.2 Internal marks fixed to MID-1 (25), MID-2 (25), Assignments (5) with frontend labels and backend validation; `internal_mark_components` rows seeded/migrated
- [x] 4.3 Automatic total `(best×0.8)+(other×0.2)+assignments` computed authoritative in backend, previewed read-only in UI, stored in numeric column; tested with `20/24/4 → 28` (ceiling)
- [x] 4.4 Faculty sidebar + header unread notification badge from the same unread-count API

## 4. Exam Admin
- [x] 5.1 Courses CSE, ECE, EEE, MECH, CIVIL, AI&ML seeded and selectable; create endpoint upper-cases codes and rejects duplicates
- [x] 5.2 Reference Data tab removed from Academic Records and no stale UI references remain
- [x] 5.3 JSON grade/pass-rule UI removed; `RegulationCreate` accepts only name/year; processing ignores regulation JSON; central pass rule `percentage < 40 → FAIL`, `≥ 40 → pass` (exactly 40 = E)
- [x] 5.4 Academic years 2023-24/2024-25/2025-26 seeded; create endpoint enforces `YYYY-YY` from 2023 and rejects duplicates; student/admin forms use year selects
- [x] 5.5 Notification Composer Audience field removed; `audience_type` defaults to `ALL` in the API so delivery still works
- [x] 5.6 External marks visibility fixed with enriched rows, filter fields and loading/empty/error states
- [x] 5.7 CSV external-mark upload: sample template, format info, validation, DB-staged preview, explicit confirm, per-row errors, applied/skipped/failed summary, audit rows, no auto-publication
- [x] 5.8 Reports/Exports and Audit Log tabs, routes, imports and sidebar links removed; backend endpoints retained for API compatibility only

## 5. Database & backend
- [x] Models + Alembic migration `0f3a7b2c9d41_workflow_updates.py` for all new fields/tables; upgrade downgrade upgrade smoke-tested on SQLite
- [x] Existing records preserved by data migration; FK integrity maintained; role authorization, backend validation, secure uploads and transactions verified

## 6. Frontend & UX
- [x] Consistent design system, labels, validation, loading/success/failure states, confirmation for CSV import, responsive layouts and accessible badges/buttons
- [x] Mock adapter updated to the new auth/receipt/correction/external-mark/CSV contracts; no stale JSON grading or audience UI references

## 7. Verification
- [x] Backend pytest (all + new tests): `47 passed, 1 warning in 184.37s` (latest full run after the institution-seed change)
- [x] Frontend typecheck / lint / production build: all pass (only the pre-existing large-chunk Vite warning)
- [x] Student workflows tested (temporary password, receipt upload/download, numeric correction, published-result recounting, badges)
- [x] Faculty workflows tested (full name, fixed components, authoritative total, numeric correction review, badges)
- [x] Admin workflows tested (courses/years, notification default audience, external marks, CSV preview/confirm/audit, recounting revision, receipt download)
- [x] Cross-module integration, role restrictions and persistence verified through the isolated DB test suite and live SQLite startup; PostgreSQL/Docker remain deployment-configured but were not run locally (no daemon)
- [x] Final implementation report written: [`FINAL_IMPLEMENTATION_REPORT.md`](FINAL_IMPLEMENTATION_REPORT.md)

## 8. Institution data seed (2026-11-23 follow-up)
- [x] Supplied faculty/subject/student data copied into `backend/app/data/` and parsed by the default seed
- [x] Demo/test data removed from the running database; old demo accounts no longer authenticate
- [x] Test dataset isolated in `seed_test_db()` and `--test-data`; pytest continues to use it only in fixtures
- [x] 30 faculty, 30 subjects, 100 students and 30 department-scoped assignments seeded into `backend/exam.db`
- [x] Login-page local/demo-accounts container, constant and form prefill removed
- [x] No fabricated exams, registrations, marks, hall tickets or notifications in the institution seed
- [x] Deterministic `name@123` credentials (admin: `admin@123`, bcrypt-hashed) written to an operator-controlled CSV; students forced to change password
- [x] Live API verification: counts, department assignment integrity, faculty subject visibility, student temp-password gate, `name@123` logins (admin `admin@123`), old demo login rejection
- [x] Latest regression run: `47 passed, 1 warning in 184.37s`; frontend typecheck/lint/build pass
- [x] Design record written: [`../specs/institution_seed_design.md`](../specs/institution_seed_design.md)
