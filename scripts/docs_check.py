"""문서 점검: 코드에서 뽑을 수 있는 목록이 문서에 빠짐없이 있는지 본다.

- API 명세(docs/API_Spec.md): 앱의 모든 엔드포인트(메서드 + 경로)가 2절 목록에 있는가, 목록에 있는데 코드에 없는
  경로는 없는가. 경로의 {evaluation_id}·{id} 같은 이름은 무시하고 자리만 비교한다. 버전 없는 옛 경로(/api/...)는
  폐기 예정 별칭이라 /api/v1/...이 있으면 된다.
- ERD(docs/ERD.md): 모든 테이블이 `**테이블**` 제목으로 있고, 그 절에 모든 칸 이름이 나오는가.
- 화면 명세(docs/screens/pages/*.md): 화면 페이지마다 "버튼 ↔ API" 절이 있고, 거기 적은 엔드포인트 ID가
  API 명세에 있는가.

실행: uv run python -m scripts.docs_check   (빠진 것이 있으면 종료 코드 1, 테스트 tests/unit/test_docs_check.py)
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_SPEC = ROOT / "docs" / "API_Spec.md"
ERD = ROOT / "docs" / "ERD.md"
SCREENS = ROOT / "docs" / "screens" / "pages"
METHODS = ("get", "post", "put", "patch", "delete")
# 프레임워크가 스스로 여는 문서 경로 (기능 엔드포인트가 아님)
IGNORED_PATHS = {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}
HIDDEN_OK = {"/healthz"}  # 로드밸런서·컨테이너 상태 확인 (docs/deploy-aws.md)
# 표가 아닌 칸: 모든 테이블에 붙는 공통 칸 (ERD 1절에서 한 번 설명)
COMMON_COLUMNS = {"id", "created_at", "updated_at"}


def normalize(path: str) -> str:
    return re.sub(r"\{[^}]*\}", "{}", path.split("?")[0].rstrip("/") or "/")


def code_endpoints() -> set[tuple[str, str]]:
    from fastapi.routing import APIRoute

    from backend.main import app

    out = set()
    # 문서 화면(OpenAPI)에서 숨긴 경로도 센다 (서비스 워커 /sw.js 등). 상태 확인 /healthz는 운영용이라 뺀다
    for route in app.routes:
        if isinstance(route, APIRoute) and not route.include_in_schema and route.path not in HIDDEN_OK:
            out |= {(m, normalize(route.path)) for m in route.methods if m.lower() in METHODS}
    for path, ops in app.openapi()["paths"].items():
        if path in IGNORED_PATHS:
            continue
        if path.startswith("/api/") and not path.startswith("/api/v1/"):
            continue  # 옛 경로 별칭 (API 명세 2.7)
        for method in ops:
            if method in METHODS:
                out.add((method.upper(), normalize(path)))
    return out


# 2절 표의 한 줄: | ID | 메서드 | `경로` | ...
SPEC_ROW = re.compile(r"^\|\s*([A-Z]\d+)\s*\|\s*(GET|POST|PUT|PATCH|DELETE)\s*\|\s*`([^`]+)`")


def spec_endpoints() -> dict[tuple[str, str], str]:
    text = API_SPEC.read_text(encoding="utf-8")
    section = text.split("## 2. 엔드포인트 목록", 1)[1].split("\n## 3.", 1)[0]
    out = {}
    for line in section.splitlines():
        m = SPEC_ROW.match(line)
        if m:
            out[(m.group(2), normalize(m.group(3)))] = m.group(1)
    return out


def api_problems() -> list[str]:
    code, spec = code_endpoints(), spec_endpoints()
    problems = [f"API 명세에 없는 엔드포인트: {m} {p}" for m, p in sorted(code - spec.keys())]
    problems += [
        f"코드에 없는 엔드포인트가 API 명세에 있음: {spec[k]} {k[0]} {k[1]}" for k in sorted(spec.keys() - code)
    ]
    return problems


def erd_problems() -> list[str]:
    import backend.models  # noqa: F401 (모든 모델을 메타데이터에 올림)
    from backend.db.base import Base

    text = ERD.read_text(encoding="utf-8")
    # 테이블 절: `**테이블**` 제목부터 다음 굵은 제목까지. `**syllabi 증거 상태 (0012)**`처럼 같은 테이블을 이어
    # 설명하는 제목은 그 테이블 절로 합친다
    heads = [(m.group(1), m.start()) for m in re.finditer(r"^\*\*([a-z_]+)\b[^*\n]*\*\*", text, re.M)]
    ordered = [s for _, s in heads]
    sections: dict[str, str] = {}
    for name, begin in heads:
        end = next((s for s in ordered if s > begin), len(text))
        sections[name] = sections.get(name, "") + text[begin:end]
    problems = []
    for table in sorted(Base.metadata.tables.values(), key=lambda t: t.name):
        if table.name not in sections:
            problems.append(f"ERD에 없는 테이블: {table.name}")
            continue
        body = sections[table.name]
        for column in table.columns:
            if column.name in COMMON_COLUMNS:
                continue
            if not re.search(rf"(?<![a-z_]){re.escape(column.name)}(?![a-z_])", body):
                problems.append(f"ERD {table.name} 절에 없는 칸: {column.name}")
    return problems


def screen_problems() -> list[str]:
    ids = set(spec_endpoints().values()) | {f"J{i}" for i in range(1, 4)}
    problems = []
    for page in sorted(SCREENS.glob("*.md")):
        text = page.read_text(encoding="utf-8")
        if "## 버튼 ↔ API" not in text:
            problems.append(f"{page.name}: '버튼 ↔ API' 절이 없음")
            continue
        section = text.split("## 버튼 ↔ API", 1)[1]
        for ref in sorted(set(re.findall(r"(?<![A-Za-z0-9])([ASRFCMJ]\d{1,2})(?![0-9])", section))):
            if ref not in ids:
                problems.append(f"{page.name}: API 명세에 없는 엔드포인트 ID {ref}")
    return problems


def main() -> int:
    problems = api_problems() + erd_problems() + screen_problems()
    for p in problems:
        print(p)
    print(f"## 문서 점검: 문제 {len(problems)}건")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
