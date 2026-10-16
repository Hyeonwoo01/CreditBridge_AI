"""근거 구절의 원본 파일 열기 (FR-25): 학생 강의계획서·1순위 후보 과목의 기준 강의계획서 원본을 브라우저에서 연다.

볼 수 있는 사람은 그 심사 건을 볼 수 있는 사람(학생 본인·소속 심사관·담당 교수)과 같다.
학생 원본을 열 때마다 감사 로그를 남긴다 (파일 이름은 넣지 않는다)."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.documents.text import CONTENT_TYPES, extension
from backend.errors import NotFoundError
from backend.i18n import gettext as tr
from backend.models import CourseEvaluation, Syllabus, User
from backend.repositories import catalog as catalog_repo
from backend.repositories import evaluations as evaluation_repo
from backend.repositories import syllabi as syllabus_repo
from backend.security.permissions import ensure_can_view_evaluation
from backend.services import audit

SIDES = ("source", "target")


@dataclass
class OriginalFile:
    file_key: str
    filename: str
    content_type: str


def _syllabus_for(session: Session, evaluation: CourseEvaluation, side: str) -> Syllabus | None:
    if side == "source":
        return syllabus_repo.get(session, evaluation.syllabus_id)
    course = (
        catalog_repo.get_course(session, evaluation.candidate_course_id) if evaluation.candidate_course_id else None
    )
    if course is None or course.reference_syllabus_id is None:
        return None
    return syllabus_repo.get(session, course.reference_syllabus_id)


def open_original(session: Session, user: User, evaluation_id: int, side: str) -> OriginalFile:
    evaluation = evaluation_repo.get(session, evaluation_id)
    if evaluation is None or side not in SIDES:
        raise NotFoundError(tr("원본 파일을 찾을 수 없어요."))
    ensure_can_view_evaluation(session, user, evaluation)
    syllabus = _syllabus_for(session, evaluation, side)
    if syllabus is None or not syllabus.source_file_key:
        raise NotFoundError(tr("원본 파일이 없어요. 개인정보 삭제 요청으로 지워졌거나 텍스트로만 등록된 문서예요."))
    ext = extension(syllabus.original_filename) or extension(syllabus.source_file_key)
    if side == "source":
        audit.record(session, user, "syllabus.original_view", "syllabus", str(syllabus.id), evaluation=evaluation.id)
        session.commit()
    return OriginalFile(
        file_key=syllabus.source_file_key,
        filename=syllabus.original_filename or f"syllabus{ext}",
        content_type=CONTENT_TYPES.get(ext, "application/octet-stream"),
    )
