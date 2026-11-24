"""Backfill examination_id on internal marks and submissions.

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c2d3e4f5a6b7"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None

_EXAM_FOR_SUBJECT = (
    "SELECT es.examination_id FROM examination_subjects es "
    "WHERE es.subject_id = {table}.subject_id AND es.is_eligible IS TRUE LIMIT 1"
)


def upgrade() -> None:
    bind = op.get_bind()
    for table in ("internal_marks", "marks_submissions"):
        bind.execute(sa.text(
            f"UPDATE {table} SET examination_id = ({_EXAM_FOR_SUBJECT.format(table=table)}) "
            "WHERE examination_id IS NULL"
        ))


def downgrade() -> None:
    # The backfill only fills previously NULL values; it is not reversible
    # without distinguishing which rows were already linked.
    pass
