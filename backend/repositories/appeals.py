from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.errors import DuplicateRowError, is_duplicate
from backend.models import Appeal, AppealFile, CourseEvaluation, Syllabus, TransferRequest


def add(session: Session, appeal: Appeal) -> Appeal:
    """처리 중인 건이 이미 있으면 DuplicateRowError (앱 검사 뒤 동시 요청은 DB 유니크가 막는다)."""
    try:
        with session.begin_nested():
            session.add(appeal)
    except IntegrityError as exc:
        if is_duplicate(exc):
            raise DuplicateRowError from exc
        raise
    return appeal


def get(session: Session, appeal_id: int) -> Appeal | None:
    return session.get(Appeal, appeal_id)


def for_evaluation(session: Session, evaluation_id: int) -> list[Appeal]:
    stmt = select(Appeal).where(Appeal.course_evaluation_id == evaluation_id).order_by(Appeal.id)
    return list(session.scalars(stmt))


def latest_for_evaluations(session: Session, evaluation_ids: list[int]) -> dict[int, Appeal]:
    if not evaluation_ids:
        return {}
    stmt = select(Appeal).where(Appeal.course_evaluation_id.in_(evaluation_ids)).order_by(Appeal.id)
    return {a.course_evaluation_id: a for a in session.scalars(stmt)}


def of_institution(
    session: Session, target_institution_id: int, exclude_closed: bool = False
) -> list[tuple[Appeal, CourseEvaluation, Syllabus, TransferRequest]]:
    """exclude_closed: 문서 삭제로 종료된 요청의 이의 신청은 뺀다 (처리 목록·배지)."""
    stmt = (
        select(Appeal, CourseEvaluation, Syllabus, TransferRequest)
        .join(CourseEvaluation, CourseEvaluation.id == Appeal.course_evaluation_id)
        .join(Syllabus, Syllabus.id == CourseEvaluation.syllabus_id)
        .join(TransferRequest, TransferRequest.id == CourseEvaluation.transfer_request_id)
        .where(TransferRequest.target_institution_id == target_institution_id)
        .order_by(Appeal.id.desc())
    )
    if exclude_closed:
        stmt = stmt.where(TransferRequest.status != "closed")
    return [(a, e, s, r) for a, e, s, r in session.execute(stmt)]


def of_student(session: Session, student_id: int) -> list[tuple[Appeal, CourseEvaluation, Syllabus, TransferRequest]]:
    """학생 본인의 이의 신청. 문서 삭제로 종료된 요청의 이의 신청은 함께 지운 것으로 보고 뺀다."""
    stmt = (
        select(Appeal, CourseEvaluation, Syllabus, TransferRequest)
        .join(CourseEvaluation, CourseEvaluation.id == Appeal.course_evaluation_id)
        .join(Syllabus, Syllabus.id == CourseEvaluation.syllabus_id)
        .join(TransferRequest, TransferRequest.id == CourseEvaluation.transfer_request_id)
        .where(Appeal.student_id == student_id, TransferRequest.status != "closed")
        .order_by(Appeal.id.desc())
    )
    return [(a, e, s, r) for a, e, s, r in session.execute(stmt)]


def add_file(session: Session, file: AppealFile) -> AppealFile:
    session.add(file)
    session.flush()
    return file


def get_file(session: Session, file_id: int) -> AppealFile | None:
    return session.get(AppealFile, file_id)


def files_for(session: Session, appeal_ids: list[int]) -> dict[int, list[AppealFile]]:
    if not appeal_ids:
        return {}
    out: dict[int, list[AppealFile]] = {}
    stmt = select(AppealFile).where(AppealFile.appeal_id.in_(appeal_ids)).order_by(AppealFile.id)
    for f in session.scalars(stmt):
        out.setdefault(f.appeal_id, []).append(f)
    return out


def of_request(session: Session, request_id: int) -> list[Appeal]:
    stmt = (
        select(Appeal)
        .join(CourseEvaluation, CourseEvaluation.id == Appeal.course_evaluation_id)
        .where(CourseEvaluation.transfer_request_id == request_id)
    )
    return list(session.scalars(stmt))


def files_of_request(session: Session, request_id: int) -> list[AppealFile]:
    stmt = (
        select(AppealFile)
        .join(Appeal, Appeal.id == AppealFile.appeal_id)
        .join(CourseEvaluation, CourseEvaluation.id == Appeal.course_evaluation_id)
        .where(CourseEvaluation.transfer_request_id == request_id)
    )
    return list(session.scalars(stmt))
