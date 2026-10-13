"""공통 커스텀 타입. (파일럿에서 임베딩 검색을 붙일 때 VECTOR 타입을 이 파일에 추가한다)"""

from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.types import Text

# 강의계획서 원문처럼 긴 텍스트 (MariaDB/MySQL: LONGTEXT)
LongText = Text().with_variant(LONGTEXT(), "mysql", "mariadb")
