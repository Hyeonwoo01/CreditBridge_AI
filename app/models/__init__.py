"""모든 모델을 등록한다 (Alembic, 관계 해석용)."""

from app.models.assignment import Assignment
from app.models.audit_log import AuditLog
from app.models.course import Course
from app.models.course_evaluation import CourseEvaluation
from app.models.decision import Decision
from app.models.evidence_span import EvidenceSpan
from app.models.institution import Institution
from app.models.syllabus import Syllabus
from app.models.syllabus_chunk import SyllabusChunk
from app.models.transcript_entry import TranscriptEntry
from app.models.transfer_request import TransferRequest
from app.models.user import User

__all__ = [
    "Assignment",
    "AuditLog",
    "Course",
    "CourseEvaluation",
    "Decision",
    "EvidenceSpan",
    "Institution",
    "Syllabus",
    "SyllabusChunk",
    "TranscriptEntry",
    "TransferRequest",
    "User",
]
