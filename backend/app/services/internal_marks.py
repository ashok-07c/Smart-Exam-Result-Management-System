"""Authoritative internal marks component structure and calculation.

Internal assessment is always out of 30 marks and consists of exactly three
components with fixed maxima. Faculty cannot change the structure or the
calculated total; the backend derives it from the individual components.
"""
from __future__ import annotations

import math

from app.core.exceptions import ValidationError
from app.services.grading import round_value

INTERNAL_COMPONENTS: tuple[tuple[str, float], ...] = (
    ("MID-1", 25.0),
    ("MID-2", 25.0),
    ("Assignments", 5.0),
)
INTERNAL_MAX_MARKS = 30.0

COMPONENT_KEYS = {
    "mid1": "MID-1",
    "mid2": "MID-2",
    "assignments": "Assignments",
    "MID-1": "MID-1",
    "MID-2": "MID-2",
    "Assignments": "Assignments",
}


def calculate_internal_total(mid1: float, mid2: float, assignments: float) -> float:
    """(best MID x 0.8) + (other MID x 0.2) + assignments, rounded up to a whole mark.

    The institution requires the internal total to be rounded to the next
    integer (ceiling). An exact integer is left unchanged; 27.2 becomes 28.
    """
    best = max(float(mid1), float(mid2))
    other = min(float(mid1), float(mid2))
    derived = round_value(best * 0.8 + other * 0.2 + float(assignments))
    return float(math.ceil(derived))


def validate_components(mid1: float, mid2: float, assignments: float) -> tuple[float, float, float]:
    values = (mid1, mid2, assignments)
    if any(v is None for v in values):
        raise ValidationError("MID-1, MID-2 and Assignments are all required")
    maxima = [maximum for _, maximum in INTERNAL_COMPONENTS]
    labels = [name for name, _ in INTERNAL_COMPONENTS]
    checked: list[float] = []
    for label, value, maximum in zip(labels, values, maxima):
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ValidationError(f"{label} must be a number")
        if number != number or number in (float("inf"), float("-inf")):
            raise ValidationError(f"{label} must be a finite number")
        if number < 0:
            raise ValidationError(f"{label} cannot be negative")
        if number > maximum:
            raise ValidationError(f"{label} cannot exceed the maximum of {maximum:g}")
        checked.append(round_value(number))
    return checked[0], checked[1], checked[2]


def component_marks(mid1: float, mid2: float, assignments: float) -> dict[str, float]:
    """Readable JSON snapshot retained for existing display contracts."""
    return {"MID-1": mid1, "MID-2": mid2, "Assignments": assignments}


def assessment_configuration() -> dict:
    return {"components": [{"name": name, "max_marks": int(maximum)} for name, maximum in INTERNAL_COMPONENTS]}
