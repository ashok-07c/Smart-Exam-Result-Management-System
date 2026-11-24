"""Aggregate all v1 routers."""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin_academic,
    admin_exams,
    admin_records,
    auth,
    notifications,
    student,
    faculty,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(student.router, prefix="/students", tags=["Student Portal"])
api_router.include_router(faculty.router, prefix="/faculty", tags=["Faculty Portal"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(admin_records.router, prefix="/admin", tags=["Examination Admin - Records"])
api_router.include_router(admin_exams.router, prefix="/admin", tags=["Examination Admin - Exams"])
api_router.include_router(admin_academic.router, prefix="/admin", tags=["Examination Admin - Academic"])
