"""Exam/marks workflow updates: 70-mark externals, ceiling totals, branchless exams.

Revision ID: b1c2d3e4f5a6
Revises: 0f3a7b2c9d41
"""
from __future__ import annotations

import json
import math
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision = "b1c2d3e4f5a6"
down_revision = "0f3a7b2c9d41"
branch_labels = None
depends_on = None

COMMON_CRITERIA_KEYS = {"eligible_branches", "eligible_semesters", "min_semester"}
LEGACY_BRANCH_KEY = "_legacy_branch_id"
LEGACY_CRITERIA_KEY = "_legacy_eligibility_criteria"


def _as_dict(value) -> dict:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except ValueError:
            return {}
    return {}


def _json_statement(statement: str, parameter: str):
    """Bind a Python object to a JSON column through SQLAlchemy's type processor."""
    return sa.text(statement).bindparams(sa.bindparam(parameter, type_=sa.JSON()))


def _round2(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _ceiling_total(mid1: float, mid2: float, assignments: float) -> float:
    best, other = max(mid1, mid2), min(mid1, mid2)
    return float(math.ceil(_round2(best * 0.8 + other * 0.2 + assignments)))


def upgrade() -> None:
    bind = op.get_bind()

    # Internal remains 30; external moves from 60 to 70, keeping the grand total at 100.
    bind.execute(sa.text("UPDATE subjects SET internal_max_marks = 30, external_max_marks = 70"))

    for row in bind.execute(sa.text("SELECT id, subject_id FROM external_marks")).fetchall():
        maximum = bind.execute(
            sa.text("SELECT external_max_marks FROM subjects WHERE id = :id"), {"id": row.subject_id}
        ).scalar()
        bind.execute(
            sa.text("UPDATE external_marks SET max_marks = :maximum WHERE id = :id"),
            {"id": row.id, "maximum": maximum or 70},
        )

    for row in bind.execute(
        sa.text("SELECT id, mid1_marks, mid2_marks, assignments_marks FROM internal_marks")
    ).fetchall():
        total = _ceiling_total(
            float(row.mid1_marks or 0), float(row.mid2_marks or 0), float(row.assignments_marks or 0)
        )
        bind.execute(
            sa.text("UPDATE internal_marks SET total_marks = :total WHERE id = :id"),
            {"id": row.id, "total": total},
        )

    # Keep stored results consistent with the recalculated internal totals.
    for row in bind.execute(
        sa.text("SELECT sr.id, sr.external_marks, im.total_marks FROM subject_results sr "
                "JOIN semester_results semres ON semres.id = sr.semester_result_id "
                "JOIN internal_marks im ON im.student_id = semres.student_id "
                "AND im.subject_id = sr.subject_id AND im.examination_id = semres.examination_id")
    ).fetchall():
        internal = float(row.total_marks or 0)
        external = float(row.external_marks or 0)
        bind.execute(
            sa.text("UPDATE subject_results SET internal_marks = :internal, total_marks = :total WHERE id = :id"),
            {"id": row.id, "internal": internal, "total": internal + external},
        )

    # Every academic year from 2023 through the current year is available.
    bind.execute(sa.text("UPDATE academic_years SET status = 'ARCHIVED' WHERE status = 'ACTIVE'"))
    if not bind.execute(
        sa.text("SELECT 1 FROM academic_years WHERE academic_year_name = '2026-27'")
    ).scalar():
        bind.execute(
            sa.text(
                "INSERT INTO academic_years (id, academic_year_name, start_date, end_date, status) "
                "VALUES (:id, '2026-27', :start_date, :end_date, 'ACTIVE')"
            ),
            {
                "id": str(uuid4()),
                "start_date": date(2026, 8, 1),
                "end_date": date(2027, 7, 31),
            },
        )

    # Exam announcements are common to all branches and derive semesters from subjects.
    for row in bind.execute(
        sa.text("SELECT id, branch_id, eligibility_criteria FROM examinations")
    ).fetchall():
        criteria = _as_dict(row.eligibility_criteria)
        legacy = {key: criteria.pop(key) for key in COMMON_CRITERIA_KEYS if key in criteria}
        if row.branch_id or legacy:
            criteria[LEGACY_BRANCH_KEY] = str(row.branch_id) if row.branch_id else None
            criteria[LEGACY_CRITERIA_KEY] = legacy
        bind.execute(
            _json_statement(
                "UPDATE examinations SET branch_id = NULL, eligibility_criteria = :criteria WHERE id = :id",
                "criteria",
            ),
            {"id": row.id, "criteria": criteria},
        )

    # Assignment scope follows Subject -> Course -> Branch/Semester.
    for row in bind.execute(
        sa.text(
            "SELECT fa.id, c.branch_id AS branch_id, s.semester_id, sem.academic_year_id "
            "FROM faculty_assignments fa "
            "JOIN subjects s ON s.id = fa.subject_id "
            "LEFT JOIN courses c ON c.id = s.course_id "
            "LEFT JOIN semesters sem ON sem.id = s.semester_id"
        )
    ).fetchall():
        bind.execute(
            sa.text(
                "UPDATE faculty_assignments SET branch_id = :branch_id, semester_id = :semester_id, "
                "academic_year_id = :academic_year_id WHERE id = :id"
            ),
            {
                "id": row.id, "branch_id": row.branch_id,
                "semester_id": row.semester_id, "academic_year_id": row.academic_year_id,
            },
        )

    # Normalise staged CSV previews created before the column rename.
    for row in bind.execute(sa.text("SELECT id, rows FROM external_mark_imports")).fetchall():
        stored_rows = row.rows
        if isinstance(stored_rows, str):
            try:
                stored_rows = json.loads(stored_rows)
            except ValueError:
                continue
        if not isinstance(stored_rows, list):
            continue
        changed = False
        for item in stored_rows:
            if isinstance(item, dict) and "ext" in item and "marks" not in item:
                item["marks"] = item.pop("ext")
                changed = True
        if changed:
            bind.execute(
                _json_statement("UPDATE external_mark_imports SET rows = :rows WHERE id = :id", "rows"),
                {"id": row.id, "rows": stored_rows},
            )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("UPDATE subjects SET internal_max_marks = 30, external_max_marks = 60"))
    bind.execute(sa.text("UPDATE external_marks SET max_marks = 60"))

    for row in bind.execute(
        sa.text("SELECT id, mid1_marks, mid2_marks, assignments_marks FROM internal_marks")
    ).fetchall():
        mid1, mid2 = float(row.mid1_marks or 0), float(row.mid2_marks or 0)
        best, other = max(mid1, mid2), min(mid1, mid2)
        total = _round2(best * 0.8 + other * 0.2 + float(row.assignments_marks or 0))
        bind.execute(
            sa.text("UPDATE internal_marks SET total_marks = :total WHERE id = :id"),
            {"id": row.id, "total": total},
        )

    # Restore legacy exam branch metadata that upgrade() preserved in criteria.
    for row in bind.execute(
        sa.text("SELECT id, branch_id, eligibility_criteria FROM examinations")
    ).fetchall():
        criteria = _as_dict(row.eligibility_criteria)
        legacy_branch = criteria.pop(LEGACY_BRANCH_KEY, None)
        legacy_criteria = criteria.pop(LEGACY_CRITERIA_KEY, {})
        if isinstance(legacy_criteria, dict):
            criteria.update(legacy_criteria)
        bind.execute(
            _json_statement(
                "UPDATE examinations SET branch_id = :branch_id, eligibility_criteria = :criteria WHERE id = :id",
                "criteria",
            ),
            {"id": row.id, "branch_id": legacy_branch, "criteria": criteria},
        )
