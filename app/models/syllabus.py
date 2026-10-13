from typing import Any

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Numeric, String
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Text

from app.db.base import Base, CreatedAtMixin, IdMixin, IdType, PublicIdMixin

LongText = Text().with_variant(LONGTEXT(), "mysql", "mariadb")


class Syllabus(IdMixin, PublicIdMixin, CreatedAtMixin, Base):
    """업로드된 강의계획서(학생) 또는 대상 과목의 기준 강의계획서."""

    __tablename__ = "syllabi"
    __table_args__ = (
        CheckConstraint("extracted_json IS NULL OR JSON_VALID(extracted_json)", name="extracted_json_valid"),
    )

    institution_id: Mapped[int] = mapped_column(IdType, ForeignKey("institutions.id"), index=True)
    transfer_request_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("transfer_requests.id"), index=True)
    owner_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    source_file_key: Mapped[str | None] = mapped_column(String(255))
    original_filename: Mapped[str] = mapped_column(String(255), default="")
    language: Mapped[str] = mapped_column(String(8), default="en")
    raw_text: Mapped[str] = mapped_column(LongText, default="")
    # 추출 결과에서 검색 조건에 쓰는 값은 JSON 밖 일반 컬럼으로 둔다
    course_code: Mapped[str] = mapped_column(String(50), default="", index=True)
    course_title: Mapped[str] = mapped_column(String(255), default="")
    credits: Mapped[float | None] = mapped_column(Numeric(4, 1, asdecimal=False))
    extracted_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    extraction_model: Mapped[str | None] = mapped_column(String(100))
    # 문서 인식 품질 점수 0~1 (FR-01)
    quality_score: Mapped[float | None] = mapped_column(Numeric(4, 3, asdecimal=False))
    # 판정 유도 문구 탐지 결과 (FR-14)
    injection_flags: Mapped[list[str] | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="uploaded")
    error_message: Mapped[str | None] = mapped_column(String(500))
