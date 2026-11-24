"""Import every model so SQLAlchemy's metadata is complete."""
from app.database.session import Base
from app.models.common import TimestampMixin
from app.models.enums import *  # noqa: F401,F403
from app.models.user import User, Student, Faculty
from app.models.academic import (
    Department,
    Branch,
    AcademicYear,
    Regulation,
    Semester,
    Course,
    Subject,
    FacultyAssignment,
)
from app.models.examination import (
    Examination,
    ExaminationSubject,
    ExaminationEligibility,
    ExaminationRegistration,
    RegistrationSubject,
    ExamSession,
    ExaminationVenue,
    ExaminationSchedule,
)
from app.models.marks import (
    InternalMark,
    InternalMarkComponent,
    MarksSubmission,
    StudentMarkCorrectionRequest,
)
from app.models.result import (
    ExternalMark,
    SemesterResult,
    SubjectResult,
    Backlog,
    RecountingRequest,
    RecountingRequestHistory,
)
from app.models.notification import Notification, NotificationRecipient, AuditLog
from app.models.misc import PasswordResetToken, HallTicket

__all__ = [
    "Base",
    "TimestampMixin",
    "User",
    "Student",
    "Faculty",
    "Department",
    "Branch",
    "AcademicYear",
    "Regulation",
    "Semester",
    "Course",
    "Subject",
    "FacultyAssignment",
    "Examination",
    "ExaminationSubject",
    "ExaminationEligibility",
    "ExaminationRegistration",
    "RegistrationSubject",
    "ExamSession",
    "ExaminationVenue",
    "ExaminationSchedule",
    "InternalMark",
    "InternalMarkComponent",
    "MarksSubmission",
    "StudentMarkCorrectionRequest",
    "ExternalMark",
    "SemesterResult",
    "SubjectResult",
    "Backlog",
    "RecountingRequest",
    "RecountingRequestHistory",
    "Notification",
    "NotificationRecipient",
    "AuditLog",
    "PasswordResetToken",
    "HallTicket",
]
