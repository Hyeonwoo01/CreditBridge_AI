from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import MaterialRequest, SupplementFile


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
