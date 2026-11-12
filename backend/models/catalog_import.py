from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, CreatedAtMixin, IdMixin, IdType, one_of
from backend.models.enums import CatalogImportStatus


class CatalogImport(IdMixin, CreatedAtMixin, Base):
    """대상 대학 과목 카탈로그 가져오기 한 번 (리뷰 v3 P1-2, 13.10).

    올리기(ingest) → 형식 검증(validate) → 바뀌는 점 미리 보기(review) → 게시(publish)로 나눈다. 게시 전 자료는
    AI 후보 과목에 쓰이지 않는다. 게시한 자료는 과목마다 courses.catalog_import_id로 출처를 남기고, 바뀐 값은
    changes에 이전 값과 함께 남는다 (과목 버전 이력)."""

    __tablename__ = "catalog_imports"
    __table_args__ = (CheckConstraint(one_of("status", CatalogImportStatus), name="status_valid"),)

    institution_id: Mapped[int] = mapped_column(IdType, ForeignKey("institutions.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    file_hash: Mapped[str] = mapped_column(String(64))  # 원본 파일 SHA-256 (파일 자체는 저장하지 않음)
    source: Mapped[str] = mapped_column(Text, default="")  # 출처: 학사 편람·포털 주소 등
    catalog_year: Mapped[int | None] = mapped_column(default=None)  # 적용 학년도 (올린 날짜와 다름)
    status: Mapped[str] = mapped_column(String(10), index=True)
    rows: Mapped[list[Any]] = mapped_column(JSONB)  # 검증을 통과한 행
    changes: Mapped[dict[str, Any]] = mapped_column(JSONB)  # added·changed(필드별 [이전, 새 값])·unchanged
    created_by: Mapped[int] = mapped_column(IdType, ForeignKey("users.id"))
    reviewed_by: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"), default=None)
    reviewed_at: Mapped[datetime | None] = mapped_column(default=None)
