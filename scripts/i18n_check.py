"""영어 번역 목록(backend/locales/en.json) 점검.

코드·템플릿이 쓰는 한국어 원문을 모아 빠진 번역과 안 쓰는 번역을 보여 준다.

원문을 모으는 곳: 템플릿의 _("…")·tr("…"), 파이썬의 tr("…")·N_("…")·gettext("…").
실행: uv run python -m scripts.i18n_check   (빠진 번역이 있으면 종료 코드 1)
"""

import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "backend" / "locales" / "en.json"
TEMPLATE_CALL = re.compile(r"""\b(?:_|tr)\(\s*(?:"((?:[^"\\]|\\.)*)"|'((?:[^'\\]|\\.)*)')""")
PY_FUNCS = {"tr", "N_", "gettext"}
PLACEHOLDER = re.compile(r"\{(\w+)\}")


def _unescape(text: str) -> str:
    return re.sub(r"\\(.)", r"\1", text)


def template_messages() -> dict[str, str]:
    out: dict[str, str] = {}
    for path in sorted((ROOT / "frontend" / "templates").rglob("*.html")):
        for m in TEMPLATE_CALL.finditer(path.read_text(encoding="utf-8")):
            out.setdefault(_unescape(m.group(1) if m.group(1) is not None else m.group(2)), str(path.relative_to(ROOT)))
    return out


def python_messages() -> dict[str, str]:
    out: dict[str, str] = {}
    for path in sorted((ROOT / "backend").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in PY_FUNCS
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                out.setdefault(node.args[0].value, f"{path.relative_to(ROOT)}:{node.lineno}")
    return out


def messages() -> dict[str, str]:
    return {**python_messages(), **template_messages()}


def catalog() -> dict[str, str | list[str]]:
    data: dict[str, str | list[str]] = json.loads(CATALOG.read_text(encoding="utf-8"))
    return data


def problems() -> tuple[list[str], list[str], list[str]]:
    """(빠진 원문, 안 쓰는 번역, 자리표시자가 다른 번역)"""
    used, cat = messages(), catalog()
    missing = [f"{where}: {msg}" for msg, where in used.items() if msg not in cat]
    unused = [msg for msg in cat if msg not in used]
    mismatched = []
    for msg, value in cat.items():
        values = value if isinstance(value, list) else [value]
        want = set(PLACEHOLDER.findall(msg))
        for v in values:
            if not v.strip() or set(PLACEHOLDER.findall(v)) != want:
                mismatched.append(f"{msg} → {v}")
    return missing, unused, mismatched


if __name__ == "__main__":
    missing, unused, mismatched = problems()
    for title, rows in (("빠진 번역", missing), ("안 쓰는 번역", unused), ("자리표시자가 다른 번역", mismatched)):
        print(f"## {title} {len(rows)}")
        for row in rows:
            print(row)
    sys.exit(1 if missing or mismatched else 0)
