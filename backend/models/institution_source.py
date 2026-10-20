from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base, CreatedAtMixin, IdMixin, IdType


class InstitutionSource(IdMixin, CreatedAtMixin, Base):
    """대상 대학이 ④ 출신 대학 목록에 올린 출신 대학. 대학마다 자기 목록만 보고 쓴다.

    출신 대학 행(institutions, is_target=false)은 같은 이름이면 한 줄을 함께 쓰고, 이 표가 대학별 목록을 정한다."""

    __tablename__ = "institution_sources"
    __table_args__ = (UniqueConstraint("institution_id", "source_institution_id"),)

    # 대상 대학 (유일 제약의 첫 열이라 따로 인덱스를 두지 않는다)
    institution_id: Mapped[int] = mapped_column(IdType, ForeignKey("institutions.id"))
    source_institution_id: Mapped[int] = mapped_column(IdType, ForeignKey("institutions.id"))
