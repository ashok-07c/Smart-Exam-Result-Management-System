"""Response helpers and pagination primitives."""
from __future__ import annotations

from math import ceil
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    pages: int

    @classmethod
    def build(cls, items: list[T], total: int, page: int, page_size: int) -> "Page[T]":
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=max(1, ceil(total / page_size)),
        )


def ok(data: Any = None, message: str = "Request completed successfully") -> dict[str, Any]:
    return {"success": True, "message": message, "data": data}


def as_number(value: Any, default: float = 0.0) -> float:
    """Return a JSON-safe float for SQLAlchemy Numeric/Decimal values."""
    return default if value is None else float(value)
