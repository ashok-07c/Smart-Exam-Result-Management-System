# Technical Design: Exam, Marks and Assignment Workflow Updates

## Requirements (EARS)

- While an exam is being created, when an exam admin opens the examination form, the system shall present the announcement as common to all branches and shall not ask for a branch.
- While a student views examinations, hall tickets or results, when the system resolves eligible subjects, it shall use only subjects belonging to the student's current semester and own branch/course.
- While any academic form is displayed, when the user selects an academic year or semester, the system shall not require a manual semester tab; the semester shall be inferred from the authenticated user's academic context or the selected subject.
- While an exam admin processes results, when they enter external marks, the system shall prompt for a CSV containing `rollno,subcode,marks` and shall validate marks out of 70 through the existing two-phase preview/confirm workflow.
- While a faculty member views students or enters marks for an assigned subject, when the query is executed, the system shall restrict results to students in the assigned subject's department/branch.
- While internal marks are calculated, when the three fixed components are totalled, the system shall round the total up to the next whole number.

## Decisions

- Internal maximum remains 30; external maximum changes from 60 to 70 so the grand total remains 100.
- "Round off to next integer" is implemented as ceiling, e.g. `27.2 -> 28`.
- Academic years begin at `2023-24` and include every year from 2023 onward through the current active year; the UI lists all persisted years without a semester tab.
- The faculty assignment failure was caused by the SPA sending `user_id`; the frontend now sends `faculty.id`, matching `FacultyAssignment.faculty_id`.

## Architecture

- `app/services/academic_scope.py` resolves subject scope as `Subject -> Course -> Branch -> Department` plus `Subject -> Semester`. Student eligibility, hall tickets, result subject lists, CSV validation and faculty access all call these shared helpers so the client cannot widen scope.
- Exam announcements store `branch_id = NULL`; semesters and branch/semester criteria are stripped server-side and derived from attached subjects. Schedules derive branch, semester and academic year from the selected subject.
- External marks enter only through the staged `rollno,subcode,marks` CSV contract (legacy `ext` aliases are normalised). Internal totals are ceil-rounded by `app/services/internal_marks.py`.
- Live schema/data changes are applied by Alembic revisions `b1c2d3e4f5a6` and `c2d3e4f5a6b7` after the earlier workflow revision.
- Faculty internal marks are bound to the examination that contains the assigned subject (derived server-side when the client omits `examination_id`), so result processing can match internal and external marks for the same exam. The follow-up migration backfills the link on existing rows.

## Security

- All new or changed endpoints retain `EXAM_ADMIN` / `FACULTY` role guards.
- Faculty student visibility is enforced server-side using `FacultyAssignment`, never by a client-supplied branch filter.
- CSV uploads remain preview-only until explicit admin confirmation; file type, size and path handling remain server-validated.
- Audit logging continues to record external-mark imports and result changes.

## Implementation Plan

- [x] Audit current flow and confirm faculty-assignment failure
- [x] Update backend rules, schemas and seed data
- [x] Update frontend forms, tabs and labels
- [x] Update tests and live database
- [x] Run backend and frontend verification (55 backend tests, typecheck, lint, build, live API smoke)
