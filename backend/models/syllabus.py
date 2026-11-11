from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, CreatedAtMixin, IdMixin, IdType, one_of, ratio
from backend.db.types import JSONB
from backend.models.enums import Applicability, Authenticity, SourceKind, SyllabusStatus


class Syllabus(IdMixin, CreatedAtMixin, Base):
    """업로드된 강의계획서(학생) 또는 대상 과목의 기준 강의계획서."""

    __tablename__ = "syllabi"
    __table_args__ = (
        CheckConstraint(one_of("status", SyllabusStatus), name="status_valid"),
        CheckConstraint(ratio("quality_score"), name="quality_score_range"),
        CheckConstraint("credits IS NULL OR credits >= 0", name="credits_range"),
        CheckConstraint(one_of("source_kind", SourceKind), name="source_kind_valid"),
        CheckConstraint(one_of("authenticity", Authenticity), name="authenticity_valid"),
        CheckConstraint(one_of("applicability", Applicability), name="applicability_valid"),
        # 같은 요청에 같은 문서를 두 번 올릴 수 없다. 요청이 다르면 같은 문서의 분석 결과를 재사용한다.
        UniqueConstraint("transfer_request_id", "content_hash", name="uq_syllabi_request_content"),
    )

    institution_id: Mapped[int] = mapped_column(IdType, ForeignKey("institutions.id"), index=True)
    transfer_request_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("transfer_requests.id"), index=True)
    owner_id: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    source_file_key: Mapped[str | None] = mapped_column(String(255))
    # 업로드 원본(보완 자료 포함)의 SHA-256. 같으면 LLM을 다시 호출하지 않고 저장된 결과를 쓴다
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    original_filename: Mapped[str] = mapped_column(String(255), default="")
    language: Mapped[str] = mapped_column(String(8), default="en")
    raw_text: Mapped[str] = mapped_column(Text, default="")
    # 원본 파일 페이지 위치표 [1쪽 시작, …, 마지막 쪽 끝] (FR-25 근거 구절 → 원본 PDF 페이지). 이전 업로드는 없음
    page_offsets: Mapped[list[int] | None] = mapped_column(JSONB(none_as_null=True))
    # 추출 결과에서 검색 조건에 쓰는 값은 JSON 밖 일반 컬럼으로 둔다
    course_code: Mapped[str] = mapped_column(String(50), default="", index=True)
    course_title: Mapped[str] = mapped_column(String(255), default="")
    credits: Mapped[float | None] = mapped_column(Numeric(4, 1, asdecimal=False))
    extracted_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    extraction_model: Mapped[str | None] = mapped_column(String(100))
    # 문서 인식 품질 점수 0~1 (FR-01)
    quality_score: Mapped[float | None] = mapped_column(Numeric(4, 3, asdecimal=False))
    # 판정 유도 문구 탐지 결과 (FR-14)
    injection_flags: Mapped[list[str] | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), default="uploaded")
    # 증거 출처·진위·적용 학기 (리뷰 v3 P0-5). 파일 해시는 같은 파일인지만 알려 주고 진위를 증명하지 않는다
    source_kind: Mapped[str] = mapped_column(String(30), default=SourceKind.STUDENT_UPLOADED)
    authenticity: Mapped[str] = mapped_column(String(20), default=Authenticity.UNVERIFIED)
    applicability: Mapped[str] = mapped_column(String(10), default=Applicability.UNKNOWN)
    academic_term: Mapped[str | None] = mapped_column(String(50))  # 강의계획서가 적용되는 학기 (심사관 확인)
    verification_method: Mapped[str] = mapped_column(String(200), default="")
    verification_note: Mapped[str] = mapped_column(Text, default="")
    verified_by: Mapped[int | None] = mapped_column(IdType, ForeignKey("users.id"))
    verified_at: Mapped[datetime | None]
    error_message: Mapped[str | None] = mapped_column(String(500))
