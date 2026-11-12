"""졸업 프로그램·요건 (리뷰 v3 P1-6)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import DegreeProgram, GraduationRequirement


def programs_of(session: Session, institution_id: int) -> list[DegreeProgram]:
    stmt = select(DegreeProgram).where(DegreeProgram.institution_id == institution_id).order_by(DegreeProgram.id)
    return list(session.execute(stmt).scalars())


def get_program(session: Session, program_id: int) -> DegreeProgram | None:
    return session.get(DegreeProgram, program_id)


def requirements_of(session: Session, program_ids: list[int]) -> list[GraduationRequirement]:
    if not program_ids:
        return []
    stmt = (
        select(GraduationRequirement)
        .where(GraduationRequirement.program_id.in_(program_ids))
        .order_by(GraduationRequirement.program_id, GraduationRequirement.sort, GraduationRequirement.id)
    )
    return list(session.execute(stmt).scalars())


def get_requirement(session: Session, requirement_id: int) -> GraduationRequirement | None:
    return session.get(GraduationRequirement, requirement_id)


def add(session: Session, row: DegreeProgram | GraduationRequirement) -> None:
    session.add(row)
    session.flush()


def delete(session: Session, row: DegreeProgram | GraduationRequirement) -> None:
    session.delete(row)
    session.flush()
