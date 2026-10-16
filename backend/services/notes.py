"""심사 건 내부 메모: 심사관과 담당 교수가 심사 건마다 남기는 메모 (예: "학과장 확인 중").

학생에게는 보이지 않고, 판정 근거 리포트(학생도 보는 문서)에도 넣지 않는다.
고치거나 지우지 않고 새로 남긴다. 감사 로그에는 식별자만 남기고 메모 내용은 넣지 않는다."""

from sqlalchemy.orm import Session

from backend.errors import CreditBridgeError, NotFoundError, PermissionDeniedError
from backend.i18n import gettext as tr
from backend.models import EvaluationNote, User
from backend.models.enums import Role
from backend.repositories import evaluations as evaluation_repo
from backend.repositories import notes as note_repo
from backend.security.permissions import can_view_evaluation
from backend.services import audit

MAX_LENGTH = 1000
STAFF = (Role.EVALUATOR, Role.PROFESSOR)


def for_syllabus(session: Session, syllabus_id: int) -> list[EvaluationNote]:
    return note_repo.of_syllabus(session, syllabus_id)


def add(session: Session, user: User, evaluation_id: int, body: str) -> EvaluationNote:
    evaluation = evaluation_repo.get(session, evaluation_id)
    if evaluation is None:
        raise NotFoundError(tr("심사 건을 찾을 수 없어요."))
    if user.role not in STAFF or not can_view_evaluation(session, user, evaluation):
        raise PermissionDeniedError(tr("이 심사 건에 메모를 남길 권한이 없어요."))
    body = body.strip()
    if not body:
        raise CreditBridgeError(tr("메모 내용을 적어 주세요."))
    if len(body) > MAX_LENGTH:
        raise CreditBridgeError(tr("메모는 {max_length}자까지 남길 수 있어요.", max_length=MAX_LENGTH))
    note = note_repo.add(
        session,
        EvaluationNote(
            syllabus_id=evaluation.syllabus_id, course_evaluation_id=evaluation.id, author_id=user.id, body=body
        ),
    )
    audit.record(session, user, "note.create", "course_evaluation", str(evaluation.id), note=note.id)
    session.commit()
    return note
