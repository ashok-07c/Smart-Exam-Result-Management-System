# API Contract — `/api/v1`

Generated from the running FastAPI app (`app.openapi()`), verified at **92 OpenAPI paths total**: **91 under `/api/v1` plus the unversioned `/health`**. Interactive docs are available at `/docs` and the machine-readable spec at `/openapi.json`.

## Conventions

### Base URL & versioning
- All business endpoints are prefixed with `/api/v1`; `/health` is unversioned.
- Version is in the path. No header-based versioning is used.

### Response envelope
Every JSON response uses:

```json
{ "success": true, "message": "Request completed successfully", "data": { } }
```

Errors use the same shape with `success: false` plus an optional `code` and `errors`:

```json
{ "success": false, "message": "Validation failed", "code": "validation_error",
  "errors": [{ "field": "email", "message": "value is not a valid email address" }] }
```

### Pagination
List endpoints accepting `page` (default 1) and `page_size` (default 20, max 200) return:

```json
{ "success": true, "message": "...",
  "data": { "items": [], "total": 0, "page": 1, "page_size": 20, "pages": 1 } }
```

### Status codes
- `200` success / state update · `201` resource created · `204` no-content logout
- `400` invalid operation · `401` missing/invalid token · `403` wrong role, out-of-scope resource, or temporary password still active
- `404` not found · `409` conflict (duplicate registration, locked marks, illegal state transition) · `422` validation error

### Error codes
`unauthorized`, `forbidden`, `not_found`, `conflict`, `validation_error`, `password_change_required`.

### Authentication
Send `Authorization: Bearer <access_token>` on protected routes. The refresh token is an HttpOnly cookie scoped to `/api/v1/auth` and is used only by `/auth/refresh` and `/auth/logout`.

`POST /auth/login`, `/auth/refresh` and `GET /auth/me` return a `user` object containing `full_name`, `role` and `must_change_password`. A student whose `must_change_password` is `true` may call `/auth/change-password`; all other student endpoints return `403 password_change_required` until the password is changed. The SPA enforces the same rule by routing that user to `/change-password`.

---

## System & Auth

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness and environment. |
| POST | `/auth/login` | Credentials → access token, `user`, `expires_in`; sets refresh cookie. |
| POST | `/auth/refresh` | Rotate access token using the refresh cookie. |
| POST | `/auth/logout` | Revoke refresh session and clear cookie. |
| GET | `/auth/me` | Current user record, including `must_change_password`. |
| POST | `/auth/change-password` | `{ current_password, new_password, confirm_password }`; verifies current password, enforces complexity, clears the flag. |
| POST | `/auth/forgot-password` | Issue a single-use one-hour reset token (returned only outside production). |
| POST | `/auth/reset-password` | `{ token, new_password }`. |

## Student (`/students/me`)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/students/me` | Student profile. |
| PATCH | `/students/me/profile` | Update permitted profile fields. |
| GET | `/students/me/examinations` | Examinations the student is currently eligible for. |
| GET | `/students/me/examinations/{examination_id}/subjects` | Eligible subjects for an examination. |
| GET / POST | `/students/me/registrations` | List own registrations / submit a **multipart** registration with a mandatory SBI Collect fee receipt. |
| GET | `/students/me/registrations/{registration_id}/receipt` | Download own fee receipt (binary). |
| GET | `/students/me/timetable` | Published schedule entries relevant to the student. |
| GET | `/students/me/timetable/download` | Timetable PDF. |
| GET | `/students/me/hall-tickets` | Own hall tickets. |
| GET | `/students/me/hall-tickets/{ticket_id}` | Hall ticket detail. |
| GET | `/students/me/hall-tickets/{ticket_id}/download` | Hall ticket PDF; prints the configured institution name. |
| GET | `/students/me/internal-marks` | Own internal marks, including MID-1/MID-2/Assignments and server total. |
| GET / POST | `/students/me/mark-correction-requests` | List / submit a numeric, non-JSON correction request. |
| GET | `/students/me/results` | Only `PUBLISHED` semester results. |
| GET | `/students/me/results/{result_id}` | Published result detail with subject breakdown and server-assigned grades. |
| GET | `/students/me/sgpa-cgpa` | Server-calculated SGPA/CGPA series. |
| GET | `/students/me/certificates/{result_id}/download` | Result certificate PDF; prints the configured institution name. |
| GET | `/students/me/backlogs` | Derived active/cleared backlogs. |
| GET / POST | `/students/me/recounting-requests` | List / submit recounting requests against a **published** result. |
| GET | `/students/me/notifications` | Own notifications (paginated, filterable by category/unread). |

### Registration fields (`multipart/form-data`)
- `examination_id`: UUID (form field).
- `subject_ids`: one or more UUIDs (repeated form fields).
- `fee_receipt`: required file. Accepted: PDF/JPG/JPEG/PNG, maximum 5 MB, validated again while streaming to a private upload directory.

The server re-checks eligibility, subject scope, duplicates and the registration window. The receipt is stored under a random filename; the original name is retained only for display/download. On any DB failure the new file is deleted and the transaction rolled back.

### Correction request body
```json
{ "subject_code": "CS301", "reported_marks": 24.8,
  "suggested_marks": 26.5, "explanation": "Assignment total appears incorrect." }
```
No JSON blob fields are accepted. `subject_code` is normalised and resolved to a subject for faculty routing.

### Recounting request body
```json
{ "examination_id": "<uuid>", "subject_id": "<uuid>",
  "result_id": "<uuid>", "reason": "Please verify the external total." }
```
`result_id` is optional but, when supplied, must be a published result for that examination/student. Without it the newest published result is used. The subject must be present in that result. A custom `recounting_until` in examination eligibility criteria overrides the default 30-day window from publication.

## Faculty (`/faculty/me`)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/faculty/me` | Faculty profile with authoritative `full_name`. |
| GET | `/faculty/me/assignments` | Subjects/sections assigned to this faculty member. |
| GET | `/faculty/me/classes` | Classes derived from assignments. |
| GET | `/faculty/me/students` | Students in assigned classes (paginated). |
| GET / POST | `/faculty/me/internal-marks` | Read / save internal marks using fixed components. |
| GET / POST | `/faculty/me/marks-submissions` | List / submit marks for verification (locks the marks). |
| GET | `/faculty/me/correction-requests` | Correction requests for assigned subjects. |
| PATCH | `/faculty/me/correction-requests/{request_id}` | `approve`, `reject`, `under_review` or `correct` with numeric `corrected_marks`. |
| GET | `/faculty/me/timetable` | Faculty timetable. |
| GET | `/faculty/me/notifications` | Faculty notifications. |

Every faculty endpoint resolves the faculty row from the current user and checks the requested subject/section against `FacultyAssignment`; out-of-scope IDs return `403`.

### Internal marks body
```json
{ "subject_id": "<uuid>", "examination_id": "<uuid>",
  "entries": [{ "student_id": "<uuid>", "mid1_marks": 20, "mid2_marks": 24,
                "assignments_marks": 4, "save_as_draft": true }] }
```
`examination_id` is optional: when omitted, the server derives it from the single eligible examination containing the subject. The assignment response includes the derived `examination_id`.

Maxima are fixed server-side: MID-1 = 25, MID-2 = 25, Assignments = 5 (internal total 30). The authoritative total is:

```text
ceil((best(MID-1, MID-2) × 0.8) + (other × 0.2) + Assignments)
```

For `20, 24, 4` the stored total is `28` (the unrounded value `27.2` is rounded up). The client may preview this value but cannot submit it; submitted totals are recomputed and validated server-side. Subjects use internal 30 / external 70, giving a grand total of 100.

## Shared notifications

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/notifications` | Notifications for the current user. |
| GET | `/notifications/unread-count` | `{ count }` used by the sidebar and header unread badges. |
| PATCH | `/notifications/{recipient_id}/read` | Mark one notification read. |
| POST | `/notifications/mark-all-read` | Mark all of the current user's notifications read. |

## Admin — records (`/admin`)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/admin/dashboard` | Counts and recent activity. |
| GET / POST | `/admin/students` | List / create student accounts (role forced to STUDENT). |
| GET / PATCH / DELETE | `/admin/students/{student_id}` | Student detail / update / deactivate. |
| GET / POST | `/admin/faculty` | List / create faculty accounts (role forced to FACULTY). |
| GET / PATCH / DELETE | `/admin/faculty/{faculty_id}` | Faculty detail / update / deactivate. |
| GET | `/admin/departments` | Departments. |
| GET | `/admin/branches` | Branches. |
| GET / POST | `/admin/academic-years` | List / create academic years. Create accepts `YYYY-YY` starting at 2023; duplicates return `409`. |
| GET | `/admin/semesters` | Semesters. |
| GET / POST | `/admin/regulations` | List / create regulation labels. Create accepts only `regulation_name` and `effective_year`. |
| PATCH | `/admin/regulations/{regulation_id}` | Rename a regulation label / change effective year. |
| GET / POST | `/admin/courses` | List / create courses. Codes are upper-cased and duplicates rejected; UI exposes CSE, ECE, EEE, MECH, CIVIL, AI&ML. |
| GET / POST | `/admin/subjects` | List / create subjects. Internal maxima are fixed in code; `assessment_configuration` is optional legacy data only. |
| GET / PATCH / DELETE | `/admin/subjects/{subject_id}` | Subject detail / update / delete. |
| GET / POST | `/admin/faculty-assignments` | List / create faculty subject assignments. |
| PATCH / DELETE | `/admin/faculty-assignments/{assignment_id}` | Update / remove assignment. |

`POST /admin/regulations` with legacy `grade_rules`, `pass_rules` or `calculation_rules` fields is rejected with `422`: grade/pass policy is no longer configuration data. `GET` may still return legacy JSON for existing rows, but the SPA does not render or use it.

## Admin — examinations (`/admin`)

| Method | Path | Purpose |
| --- | --- | --- |
| GET / POST | `/admin/examinations` | List / create examinations and attached subjects. |
| GET / PATCH | `/admin/examinations/{examination_id}` | Examination detail / update. |
| GET | `/admin/registrations` | Paginated registrations with receipt metadata (`has_fee_receipt`, filename, upload time). |
| PATCH | `/admin/registrations/{registration_id}` | Confirm or cancel a registration. |
| GET | `/admin/registrations/{registration_id}/receipt` | Download a student's fee receipt (binary, admin only). |
| GET / POST | `/admin/notifications` | List / publish notifications. Audience fields are optional; when omitted the server targets `ALL`. |
| GET / POST | `/admin/schedules` | List / create schedules. |
| PATCH | `/admin/schedules/{schedule_id}` | Update or publish a schedule. |
| GET | `/admin/timetables` | Schedule list. |
| POST | `/admin/timetables/publish` | Publish all schedules. |
| GET | `/admin/timetables/download` | Timetable PDF. |
| POST | `/admin/hall-tickets/generate` | Generate hall tickets for submitted registrations. |
| GET | `/admin/hall-tickets` | Hall ticket list. |
| POST | `/admin/hall-tickets/{ticket_id}/regenerate` | Invalidate and regenerate a ticket. |

## Admin — academic operations (`/admin`)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/admin/internal-marks` | All internal marks. |
| GET | `/admin/marks-verification` | Faculty marks submissions awaiting review. |
| POST | `/admin/marks-verification/{submission_id}` | `action=approve\|return\|lock` (query param). |
| GET | `/admin/marks-management` | `{ internal, external }` lists, filterable by `student_id` / `subject_id`. External rows include roll number, student name, subject code/name, examination name and academic year. |
| POST | `/admin/marks-management/external` | Bulk upsert external marks (JSON list). |
| GET | `/admin/result-processing/sample-csv` | Download a CSV template with headers `rollno,subcode,marks`. |
| POST | `/admin/result-processing/import` | Multipart CSV upload → validate + preview + DB-staged import record. No marks are written. |
| POST | `/admin/result-processing/import/{import_id}/confirm?overwrite=false` | Explicitly apply a staged import in one transaction. `overwrite=true` also updates existing marks. |
| POST | `/admin/result-processing` | Process an examination's results with central grading (`{ examination_id, student_ids? }`). |
| GET | `/admin/results` | Processed semester results. |
| POST | `/admin/result-publication/{result_id}` | `{ action: approve\|publish\|unpublish, note? }`. |
| GET | `/admin/sgpa-cgpa` | `{ results, regulations }`; the regulations array is retained for compatibility only and is not rendered in the SPA. |
| GET | `/admin/backlogs` | All backlogs. |
| PATCH | `/admin/backlogs/{backlog_id}` | Assign/clear a supplementary examination (`?supplementary_exam_id=`). |
| GET | `/admin/mark-correction-requests` | All numeric correction requests with student/subject context. |
| GET | `/admin/recounting` | All recounting requests. |
| POST | `/admin/recounting/{request_id}/process` | `{ action, admin_response?, revised_marks? }`; recomputes grade/pass/SGPA/CGPA/backlog on an approved revision. |
| GET | `/admin/reports/{report_type}` | CSV/XLSX export endpoint retained for API compatibility; no UI tab remains. |
| POST | `/admin/password-reset/initiate` | `{ user_id, reason? }`; returns a one-hour token outside production. |
| GET | `/admin/audit-logs` | Paginated audit trail endpoint retained for API compatibility; no UI tab remains. |

### CSV import contract
- File must be UTF-8 `.csv`, ≤ 5 MB and ≤ 10,000 data rows.
- Required headers (case-insensitive): `rollno`, `subcode`, `ext`.
- Validation resolves roll numbers and subject codes against the DB, checks `0 ≤ ext ≤ subject.external_max_marks`, flags duplicates and reports per-row errors.
- Preview response: `{ import_id, examination_id, examination_name, filename, rows, summary }` with row statuses `valid`, `invalid`, `skipped`.
- Confirm response: `{ import_id, applied, skipped, failed, summary }`.
- Both phases write audit rows (`EXTERNAL_MARKS_CSV_VALIDATED`, `EXTERNAL_MARKS_IMPORTED`). Confirm never triggers result processing or publication.

## Representative request bodies

```jsonc
// POST /auth/login
{ "email": "24191a0101@student.jntua.ac.in", "password": "<initial password from credentials CSV>" }

// POST /auth/change-password
{ "current_password": "Temp@123", "new_password": "New@Pass123", "confirm_password": "New@Pass123" }

// POST /students/me/registrations  (multipart/form-data, not JSON)
examination_id=<uuid>
subject_ids=<uuid>
subject_ids=<uuid>
fee_receipt=<SBI Collect receipt file>

// POST /students/me/mark-correction-requests
{ "subject_code": "CS301", "reported_marks": 27.2, "suggested_marks": 28.2,
  "explanation": "Assignment marks appear one mark short." }

// POST /faculty/me/internal-marks
{ "subject_id": "<uuid>", "examination_id": "<uuid>",
  "entries": [{ "student_id": "<uuid>", "mid1_marks": 20,
                "mid2_marks": 24, "assignments_marks": 4 }] }

// POST /admin/regulations
{ "regulation_name": "R2023", "effective_year": "2023" }

// POST /admin/notifications
{ "title": "Results published", "message": "...", "category": "RESULT", "publish": true }

// POST /admin/result-processing
{ "examination_id": "<uuid>" }

// POST /admin/result-publication/{result_id}
{ "action": "publish", "note": "Reviewed and approved" }
```

## Grading contract

Grades and pass/fail are computed only in `app/services/grading.py`. Regulation JSON is never consulted.

| Final percentage | Grade | Grade point |
| --- | --- | --- |
| > 90 | S | 10 |
| > 80 and ≤ 90 | A | 9 |
| ≥ 70 and ≤ 80 | B | 8 |
| > 60 and < 70 | C | 7 |
| > 50 and ≤ 60 | D | 6 |
| ≥ 40 and ≤ 50 | E | 5 |
| < 40 | Fail | 0 |

- Pass rule: overall percentage **≥ 40** passes; below 40 fails. Exactly 40 is therefore a passing `E`, avoiding a grade-less pass.
- Percentages are calculated from `total_marks / (internal_max_marks + external_max_marks) × 100`.
- All marks and GPA values are rounded half-up to two decimals.
- SGPA is credit-weighted over passing subjects only; CGPA is credit-weighted across published semesters plus the current result.
- Failed subjects create or increment backlogs; a later pass clears the active backlog.

## Binary responses

Timetable, hall-ticket and certificate endpoints, fee-receipt downloads, and the CSV template/report endpoints return file streams with appropriate `Content-Type` and `Content-Disposition` headers rather than the JSON envelope. The frontend `api.download()` helper attaches the access token and saves the blob.
