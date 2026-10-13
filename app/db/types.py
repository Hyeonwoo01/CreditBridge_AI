"""MariaDB VECTOR 타입. VECTOR 관련 SQLAlchemy 타입은 이 파일에서만 정의한다."""

import json
from typing import Any

from sqlalchemy import func
from sqlalchemy.engine import Dialect
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.types import UserDefinedType


class Vector(UserDefinedType[list[float]]):
    """VECTOR(dim). 쓰기는 VEC_FromText, 읽기는 VEC_ToText로 JSON 배열을 주고받는다."""

    cache_ok = True

    def __init__(self, dim: int) -> None:
        self.dim = dim

    def get_col_spec(self, **kw: Any) -> str:
        return f"VECTOR({self.dim})"

    def bind_processor(self, dialect: Dialect) -> Any:
        def process(value: list[float] | None) -> str | None:
            if value is None:
                return None
            if len(value) != self.dim:
                raise ValueError(f"vector must have {self.dim} dimensions, got {len(value)}")
            return to_vector_text(value)

        return process

    def bind_expression(self, bindvalue: Any) -> ColumnElement[Any]:
        return func.VEC_FromText(bindvalue, type_=self)

    def column_expression(self, colexpr: Any) -> ColumnElement[Any]:
        return func.VEC_ToText(colexpr, type_=self)

    def result_processor(self, dialect: Dialect, coltype: object) -> Any:
        def process(value: str | None) -> list[float] | None:
            return None if value is None else [float(x) for x in json.loads(value)]

        return process


def to_vector_text(values: list[float]) -> str:
    return "[" + ",".join(f"{v:.7g}" for v in values) + "]"
