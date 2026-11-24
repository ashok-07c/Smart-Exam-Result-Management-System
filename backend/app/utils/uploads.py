"""Secure, local file-upload handling for examination fee receipts."""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import ValidationError

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/pjpeg",
    "image/png",
}
MAX_RECEIPT_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def _extension(filename: str | None) -> str:
    return Path(filename or "").suffix.lower()


def validate_receipt(upload: UploadFile | None) -> None:
    if upload is None or not upload.filename:
        raise ValidationError("SBI Collect Fee Payment Receipt is required")
    extension = _extension(upload.filename)
    if extension not in ALLOWED_EXTENSIONS:
        raise ValidationError("Fee receipt must be a PDF, JPG or PNG file")
    content_type = (upload.content_type or "").lower()
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationError("Fee receipt has an unsupported file type")
    if upload.size is not None and upload.size > MAX_RECEIPT_SIZE_BYTES:
        raise ValidationError("Fee receipt must be 5 MB or smaller")


def save_receipt(upload: UploadFile, *, student_id, examination_id) -> tuple[str, str, str]:
    """Save to a private directory and return (relative_path, safe_name, content_type).

    The original filename is never used for storage; a random name prevents
    traversal and collisions. The caller is responsible for deleting the file
    if the surrounding transaction fails.
    """
    validate_receipt(upload)
    extension = _extension(upload.filename)
    safe_name = f"{student_id}_{examination_id}_{uuid4().hex}{extension}"
    directory = Path(settings.upload_dir).resolve() / "fee_receipts"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / safe_name
    written = 0
    with target.open("wb") as handle:
        while True:
            chunk = upload.file.read(1024 * 1024)
            if not chunk:
                break
            written += len(chunk)
            if written > MAX_RECEIPT_SIZE_BYTES:
                handle.close()
                target.unlink(missing_ok=True)
                raise ValidationError("Fee receipt must be 5 MB or smaller")
            handle.write(chunk)
    if written == 0:
        target.unlink(missing_ok=True)
        raise ValidationError("Fee receipt is empty")
    upload.file.seek(0)
    return f"fee_receipts/{safe_name}", upload.filename, (upload.content_type or "").lower()


def receipt_path(relative_path: str) -> Path:
    base = Path(settings.upload_dir).resolve()
    target = (base / relative_path).resolve()
    if base not in target.parents or not target.is_file():
        raise ValidationError("Fee receipt is not available")
    return target


def delete_receipt(relative_path: str | None) -> None:
    if not relative_path:
        return
    try:
        receipt_path(relative_path).unlink(missing_ok=True)
    except ValidationError:
        pass
