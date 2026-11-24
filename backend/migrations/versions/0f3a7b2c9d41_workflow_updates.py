"""Workflow updates: temp passwords, receipts, internal marks, CSV imports.

Revision ID: 0f3a7b2c9d41
Revises: 719c140e49c8
"""
from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP

import sqlalchemy as sa
from alembic import op

revision = "0f3a7b2c9d41"
down_revision = "719c140e49c8"
branch_labels = None
depends_on = None

NEW_COMPONENTS = [
    {"name": "MID-1", "max_marks": 25},
    {"name": "MID-2", "max_marks": 25},
    {"name": "Assignments", "max_marks": 5},
]

NUMERIC_CONVERSIONS = {
    "internal_marks": ["total_marks"],
    "internal_mark_components": ["marks_obtained"],
    "subject_results": ["internal_marks", "external_marks", "total_marks"],
    "external_marks": ["marks_obtained"],
    "recounting_requests": ["original_marks", "revised_marks"],
}


def _round(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _as_dict(value) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return {}
    return {}


def _json_param(value: dict, dialect: str):
    return json.dumps(value) if dialect == "sqlite" else value


def _add_internal_mark_columns(op_, dialect: str) -> None:
    columns = [
        sa.Column("mid1_marks", sa.Numeric(5, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("mid2_marks", sa.Numeric(5, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("assignments_marks", sa.Numeric(5, 2), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "academic_year_id", sa.Uuid(),
            sa.ForeignKey("academic_years.id") if dialect != "sqlite" else None,
            nullable=True,
        ),
        sa.Column(
            "semester_id", sa.Uuid(),
            sa.ForeignKey("semesters.id") if dialect != "sqlite" else None,
            nullable=True,
        ),
    ]
    if dialect == "sqlite":
        # SQLite cannot ALTER constraints in place; batch mode copies the table.
        with op_.batch_alter_table("internal_marks") as batch:
            for column in columns:
                batch.add_column(column)
            batch.create_foreign_key("fk_internal_marks_academic_year", "academic_years", ["academic_year_id"], ["id"])
            batch.create_foreign_key("fk_internal_marks_semester", "semesters", ["semester_id"], ["id"])
    else:
        for column in columns:
            op_.add_column("internal_marks", column)


def _drop_internal_mark_columns(op_, dialect: str) -> None:
    names = ["semester_id", "academic_year_id", "assignments_marks", "mid2_marks", "mid1_marks"]
    if dialect == "sqlite":
        with op_.batch_alter_table("internal_marks") as batch:
            batch.drop_constraint("fk_internal_marks_semester", type_="foreignkey")
            batch.drop_constraint("fk_internal_marks_academic_year", type_="foreignkey")
            for name in names:
                batch.drop_column(name)
    else:
        for name in names:
            op_.drop_column("internal_marks", name)


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    op.add_column("users", sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.text("0")))

    op.add_column("examination_registrations", sa.Column("fee_receipt_path", sa.String(length=500), nullable=True))
    op.add_column("examination_registrations", sa.Column("fee_receipt_filename", sa.String(length=255), nullable=True))
    op.add_column("examination_registrations", sa.Column("fee_receipt_content_type", sa.String(length=100), nullable=True))
    op.add_column("examination_registrations", sa.Column("fee_receipt_uploaded_at", sa.DateTime(timezone=True), nullable=True))

    _add_internal_mark_columns(op, dialect)

    op.add_column("student_mark_correction_requests", sa.Column("subject_code", sa.String(length=64), nullable=True))
    op.add_column("student_mark_correction_requests", sa.Column("reported_marks_value", sa.Numeric(6, 2), nullable=False, server_default=sa.text("0")))
    op.add_column("student_mark_correction_requests", sa.Column("suggested_marks_value", sa.Numeric(6, 2), nullable=False, server_default=sa.text("0")))

    op.create_table(
        "external_mark_imports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("admin_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("examination_id", sa.Uuid(), sa.ForeignKey("examinations.id"), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("rows", sa.JSON(), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_external_mark_imports_admin_id", "external_mark_imports", ["admin_id"])

    if dialect == "postgresql":
        for table, columns in NUMERIC_CONVERSIONS.items():
            for column in columns:
                op.alter_column(
                    table, column, existing_type=sa.Integer(),
                    type_=sa.Numeric(6, 2), postgresql_using=f"{column}::numeric",
                )

    # Data migration: keep historical records readable under the new structure.
    # Legacy component names are mapped to the new three-component template and
    # totals are recalculated with the authoritative formula.
    subjects = bind.execute(sa.text("SELECT id FROM subjects")).fetchall()
    for row in subjects:
        bind.execute(
            sa.text("UPDATE subjects SET assessment_configuration = :cfg WHERE id = :id"),
            {"id": row.id, "cfg": _json_param({"components": NEW_COMPONENTS}, dialect)},
        )

    marks = bind.execute(sa.text("SELECT id, component_marks FROM internal_marks")).fetchall()
    for row in marks:
        components = _as_dict(row.component_marks)
        mid1 = float(components.get("MID-1", components.get("Quiz 1", 0)) or 0)
        mid2 = float(components.get("MID-2", components.get("Quiz 2", 0)) or 0)
        assignments = float(components.get("Assignments", components.get("Assignment", 0)) or 0)
        best, other = max(mid1, mid2), min(mid1, mid2)
        total = _round(best * 0.8 + other * 0.2 + assignments)
        bind.execute(
            sa.text(
                "UPDATE internal_marks SET mid1_marks = :m1, mid2_marks = :m2, "
                "assignments_marks = :a, total_marks = :t, component_marks = :cfg WHERE id = :id"
            ),
            {
                "id": row.id, "m1": mid1, "m2": mid2, "a": assignments, "t": total,
                "cfg": _json_param({"MID-1": mid1, "MID-2": mid2, "Assignments": assignments}, dialect),
            },
        )

    corrections = bind.execute(
        sa.text("SELECT id, reported_marks, suggested_marks FROM student_mark_correction_requests")
    ).fetchall()
    for row in corrections:
        reported = _as_dict(row.reported_marks)
        suggested = _as_dict(row.suggested_marks)
        bind.execute(
            sa.text(
                "UPDATE student_mark_correction_requests SET reported_marks_value = :r, suggested_marks_value = :s "
                "WHERE id = :id"
            ),
            {
                "id": row.id,
                "r": float(reported.get("value", 0) or 0),
                "s": float(suggested.get("value", 0) or 0),
            },
        )


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    op.drop_index("ix_external_mark_imports_admin_id", table_name="external_mark_imports")
    op.drop_table("external_mark_imports")
    op.drop_column("student_mark_correction_requests", "suggested_marks_value")
    op.drop_column("student_mark_correction_requests", "reported_marks_value")
    op.drop_column("student_mark_correction_requests", "subject_code")
    _drop_internal_mark_columns(op, dialect)
    op.drop_column("examination_registrations", "fee_receipt_uploaded_at")
    op.drop_column("examination_registrations", "fee_receipt_content_type")
    op.drop_column("examination_registrations", "fee_receipt_filename")
    op.drop_column("examination_registrations", "fee_receipt_path")
    op.drop_column("users", "must_change_password")
