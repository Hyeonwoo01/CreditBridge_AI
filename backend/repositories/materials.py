from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import MaterialRequest, SupplementFile, Syllabus, TransferRequest


def add(session: Session, request: MaterialRequest) -> MaterialRequest:
    session.add(request)
    session.flush()
    return request


def for_syllabi(session: Session, syllabus_ids: list[int]) -> list[MaterialRequest]:
    if not syllabus_ids:
        return []
    stmt = select(MaterialRequest).where(MaterialRequest.syllabus_id.in_(syllabus_ids)).order_by(MaterialRequest.id)
    return list(session.scalars(stmt))


def open_for_syllabus(session: Session, syllabus_id: int) -> list[MaterialRequest]:
    stmt = (
        select(MaterialRequest)
        .where(MaterialRequest.syllabus_id == syllabus_id, MaterialRequest.status == "open")
        .order_by(MaterialRequest.id)
    )
    return list(session.scalars(stmt))


def add_file(session: Session, file: SupplementFile) -> None:
    session.add(file)
    session.flush()


def files_of(session: Session, syllabus_ids: list[int]) -> list[SupplementFile]:
    if not syllabus_ids:
        return []
    return list(session.scalars(select(SupplementFile).where(SupplementFile.syllabus_id.in_(syllabus_ids))))


def open_before(
    session: Session, target_institution_id: int, before: datetime
) -> list[tuple[MaterialRequest, Syllabus]]:
    """그 대상 대학에서 before보다 먼저 보냈는데 아직 학생이 답하지 않은 보완 자료 요청."""
    stmt = (
        select(MaterialRequest, Syllabus)
        .join(Syllabus, Syllabus.id == MaterialRequest.syllabus_id)
        .join(TransferRequest, TransferRequest.id == Syllabus.transfer_request_id)
        .where(
            TransferRequest.target_institution_id == target_institution_id,
            MaterialRequest.status == "open",
            MaterialRequest.created_at < before,
        )
        .order_by(MaterialRequest.id)
    )
    return [(m, s) for m, s in session.execute(stmt)]
