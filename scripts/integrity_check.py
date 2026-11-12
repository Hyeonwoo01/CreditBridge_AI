"""중복 저장 값 정합성 점검 (ERD R2): 두 곳에 둔 값이 어긋난 행의 id를 보여 준다. 읽기만 한다.

실행: uv run python -m scripts.integrity_check   (어긋난 곳이 있으면 종료 코드 1)
운영 서버: docker compose -f docker-compose.prod.yml exec web uv run --no-group dev python -m scripts.integrity_check
출력에는 점검 이름·테이블·행 id만 있다 (이름·학번·문서 내용 없음).
"""

import sys

from backend.db.session import SessionLocal
from backend.repositories import integrity as integrity_repo
from backend.services import integrity


def main() -> int:
    with SessionLocal() as session:
        problems = integrity.run(session)
    for p in problems:
        shown = ", ".join(str(i) for i in p.ids)
        more = " …" if p.count > len(p.ids) else ""
        print(f"[{p.name}] {p.description}: {p.table} {p.count}행 어긋남 (id {shown}{more})")
    print(f"## 정합성 점검 {len(integrity_repo.CHECKS)}개: 어긋난 점검 {len(problems)}개")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
