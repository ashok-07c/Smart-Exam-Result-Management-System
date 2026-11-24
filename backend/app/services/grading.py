"""Central grading engine for the Smart Examination & Result Management System.

The backend is the single authority for grades and pass/fail decisions. The
institution's published grading scale is fixed in code so that no JSON form or
per-request configuration can change the meaning of a result.

Interpretation of the required scale (percentage of the maximum marks):

    S    > 90
    A    > 80 and <= 90
    B    >= 70 and <= 80            (the requirement states "70 and above")
    C    > 60 and <= 70
    D    > 50 and <= 60
    E    > 40 and <= 50, including exactly 40 (see below)
    Fail < 40

Pass rule: an overall percentage below 40 is a FAIL; 40 and above is a pass.
Because the pass rule explicitly protects exactly 40 while the "E" band is
worded as "greater than 40", the boundary value of exactly 40 is assigned the
grade E. This avoids a grade-less passing result and is applied everywhere.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.models.result import SemesterResult, SubjectResult

ROUNDING_DIGITS = 2
PASS_PERCENTAGE = 40.0

# (grade, minimum percentage, grade point, counts for SGPA)
# Interpreted by grade_for() using the strict/inclusive boundaries documented above.
GRADE_SCALE: tuple[tuple[str, float, float, bool], ...] = (
    ("S", 90.0, 10.0, True),
    ("A", 80.0, 9.0, True),
    ("B", 70.0, 8.0, True),
    ("C", 60.0, 7.0, True),
    ("D", 50.0, 6.0, True),
    ("E", 40.0, 5.0, True),
    ("Fail", 0.0, 0.0, False),
)


def round_value(value: float, digits: int = ROUNDING_DIGITS) -> float:
    """Round using ROUND_HALF_UP consistently across the application."""
    quantum = Decimal(1).scaleb(-digits)
    return float(Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP))


class GradeConfig:
    """Stateless facade kept for API compatibility with existing call sites.

    The optional ``regulation`` argument is accepted so older code keeps
    working, but it is deliberately ignored: grade and pass rules are no longer
    configured through JSON.
    """

    def __init__(self, regulation=None) -> None:
        self.regulation = regulation
        self.grade_rules = [{"grade": g, "min_percentage": p, "grade_point": gp} for g, p, gp, _ in GRADE_SCALE]
        self.pass_rules = {"overall_min_percentage": PASS_PERCENTAGE}
        self.calculation_rules = {"rounding_digits": ROUNDING_DIGITS, "cgpa_mode": "credit_weighted_all"}

    @property
    def rounding_digits(self) -> int:
        return ROUNDING_DIGITS

    def round(self, value: float) -> float:
        return round_value(value)

    def grade_for(self, percentage: float) -> tuple[str, float, bool]:
        value = round_value(float(percentage))
        if value > 90:
            return _grade("S")
        if value > 80:
            return _grade("A")
        if value >= 70:
            return _grade("B")
        if value > 60:
            return _grade("C")
        if value > 50:
            return _grade("D")
        if value >= 40:
            return _grade("E")
        return _grade("Fail")

    def is_pass(
        self,
        internal: float,
        internal_max: int,
        external: float,
        external_max: int,
        total: float,
        total_max: int,
    ) -> bool:
        """Pass if and only if overall percentage is at least 40."""
        percentage = (float(total) / float(total_max) * 100) if total_max else 0.0
        return round_value(percentage) >= PASS_PERCENTAGE


def _grade(name: str) -> tuple[str, float, bool]:
    for grade, _minimum, point, counts in GRADE_SCALE:
        if grade == name:
            return grade, point, counts
    raise ValueError(f"Unknown grade {name}")


def percentage_of(total: float, maximum: int) -> float:
    return (float(total) / float(maximum) * 100) if maximum else 0.0


def calculate_sgpa(results: list[SubjectResult], config: GradeConfig | None = None) -> tuple[float, int, int]:
    engine = config or GradeConfig()
    numerator = 0.0
    denominator = 0
    earned = 0
    for result in results:
        if result.result_status != "PASS":
            continue
        if result.grade == "Fail":
            continue
        numerator += result.credits * float(result.grade_point)
        denominator += result.credits
        earned += result.credits
    sgpa = (numerator / denominator) if denominator else 0.0
    return engine.round(sgpa), int(denominator), earned


def calculate_cgpa(
    previous: list[SemesterResult],
    current_sgpa: float,
    current_credits: int,
    config: GradeConfig | None = None,
) -> float:
    engine = config or GradeConfig()
    points = 0.0
    credits = 0
    for result in previous:
        if result.sgpa is None:
            continue
        points += float(result.sgpa) * result.total_credits
        credits += result.total_credits
    if current_credits:
        points += current_sgpa * current_credits
        credits += current_credits
    return engine.round(points / credits) if credits else 0.0
