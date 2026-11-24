# Technical Design: Institution Data Seed

## Goal

Replace the demo/test population used by the running app with the supplied institution data, remove the local-account panel from the login screen, and create department-scoped faculty assignments for every supplied subject.

## Data mapping

| Supplied file | Target tables | Notes |
| --- | --- | --- |
| `faculty.txt` | `users`, `faculty`, `departments`, `branches` | 30 faculty across CSE, EEE, ECE, CIVIL and MECHANICAL. `MECHANICAL` is normalised to the existing course code `MECH`. |
| `sub data.txt` | `subjects`, `courses`, `semesters` | 30 subjects. Semester is inferred from the first digit in the subject code (`CSE501` → 5, `EEE201` → 2, `ECE401` → 4, `CIV101` → 1, `ME301` → 3). |
| `student data.txt` | `users`, `students` | 100 students, 20 per branch. Roll numbers are kept exactly as supplied. Admission year is inferred as `2024-25` from the `24` roll prefix. |

Academic structure kept from the existing system: years 2023-24/2024-25/2025-26 and the six selectable courses, including `AI&ML`. No faculty, subjects or students are invented for `AI&ML` because none were supplied.

## Assignment rule

For each branch, the supplied faculty are assigned one-to-one to the supplied subjects in file order. A `FacultyAssignment` is only created when `faculty.department_id == subject.branch.department_id`; an assertion enforces this before commit. This gives every subject exactly one teacher from its own department.

## Test data removal

- `seed_test_db()` remains **only** as the pytest fixture used by `tests/conftest.py`; it is never called by the running app.
- The default CLI command now calls `seed_institution_db()`.
- The login-page container that displayed hard-coded local accounts is removed, along with its `demoAccounts` constant and form prefill logic.

## Security

- The institution seed uses simple, predictable local credentials: `admin@123` for the exam admin and `<name>@123` for every other account (titles removed, spaces replaced with dots). Passwords are bcrypt-hashed before persistence and written to an operator-supplied credentials file (or printed when requested). They must be replaced before deployment. Duplicate names (for example a faculty member and a student with the same name) intentionally share a password; the unique email is the login identifier.
- All seeded students get `must_change_password=True`; the existing change-password workflow forces rotation at first login. Faculty/admin can rotate their passwords through `/auth/change-password`.
- Passwords are bcrypt-hashed before persistence.
- Emails are generated from roll numbers/name slugs under configurable domains; collisions are disambiguated and uniqueness is enforced by the existing DB constraints.
- The seed refuses to run against a non-empty database, preventing accidental mixing of demo and institution data.

## Frontend/Backend split

- Backend: data files, seed functions, CLI, conftest fixture update, real DB reseed.
- Frontend: remove the local-accounts panel from `LoginPage` only; no API or role logic changes.
- Docs: update READMEs and verification records so demo-account instructions are marked test-only.
