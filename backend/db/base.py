from collections.abc import Iterable
from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# 내부 PK/FK: BIGINT (PostgreSQL은 기본키에 IDENTITY 자동 증가)
IdType = BigInteger()


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)
    # 모든 시각은 UTC, 시간대 없는 TIMESTAMP(마이크로초까지)
    type_annotation_map = {datetime: DateTime()}  # noqa: RUF012


def one_of(column: str, values: Iterable[str], *, nullable: bool = False) -> str:
    """CHECK 제약 식: 값이 허용 목록 안에 있어야 한다."""
    listed = f"{column} IN ({', '.join(repr(str(v)) for v in values)})"
    return f"{column} IS NULL OR {listed}" if nullable else listed


def ratio(column: str) -> str:
    """CHECK 제약 식: 0~1 사이 점수 (비어 있어도 된다)."""
    return f"{column} IS NULL OR {column} BETWEEN 0 AND 1"


class IdMixin:
    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
