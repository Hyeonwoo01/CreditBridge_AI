"""공통 커스텀 타입. (파일럿에서 임베딩 검색을 붙일 때 VECTOR 타입을 이 파일에 추가한다)

긴 글(강의계획서 원문 등)은 PostgreSQL TEXT를 그대로 쓴다(길이 제한 없음). JSON 값은 JSONB.
"""

from sqlalchemy.dialects.postgresql import JSONB

__all__ = ["JSONB"]
