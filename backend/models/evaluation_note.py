from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, CreatedAtMixin, IdMixin, IdType


class EvaluationNote(IdMixin, CreatedAtMixin, Base):
    """심사 건 내부 메모 (심사관·담당 교수끼리, 학생에게는 보이지 않음).

    재분석해도 같은 심사 건에 이어지도록 강의계획서 단위로 모은다. 고치거나 지우지 않고 새로 남기며,
    개인정보 삭제 요청이 승인되면 문서와 함께 지운다."""

    __tablename__ = "evaluation_notes"

    syllabus_id: Mapped[int] = mapped_column(IdType, ForeignKey("syllabi.id"), index=True)
    course_evaluation_id: Mapped[int] = mapped_column(IdType, ForeignKey("course_evaluations.id"))
    author_id: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
