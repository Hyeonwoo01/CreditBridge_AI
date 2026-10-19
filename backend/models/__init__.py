"""모든 모델을 등록한다 (Alembic, 관계 해석용)."""

from backend.models.appeal import Appeal
from backend.models.appeal_file import AppealFile
from backend.models.assignment import Assignment
from backend.models.audit_log import AuditLog
from backend.models.course import Course
from backend.models.course_evaluation import CourseEvaluation
from backend.models.decision import Decision
from backend.models.department import Department
from backend.models.equivalency import Equivalency
from backend.models.evaluation_note import EvaluationNote
from backend.models.evidence_span import EvidenceSpan
from backend.models.institution import Institution
from backend.models.material_request import MaterialRequest
from backend.models.notification import Notification
from backend.models.privacy_request import PrivacyRequest
from backend.models.push_subscription import PushSubscription
from backend.models.supplement_file import SupplementFile
from backend.models.syllabus import Syllabus
from backend.models.syllabus_chunk import SyllabusChunk
from backend.models.transcript_entry import TranscriptEntry
from backend.models.transfer_request import TransferRequest
from backend.models.user import User

__all__ = [
    "Appeal",
    "AppealFile",
    "Assignment",
    "AuditLog",
    "Course",
    "CourseEvaluation",
    "Decision",
    "Department",
    "Equivalency",
    "EvaluationNote",
    "EvidenceSpan",
    "Institution",
    "MaterialRequest",
    "Notification",
    "PrivacyRequest",
    "PushSubscription",
    "SupplementFile",
    "Syllabus",
    "SyllabusChunk",
    "TranscriptEntry",
    "TransferRequest",
    "User",
]
