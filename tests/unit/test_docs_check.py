"""문서 점검 (scripts/docs_check.py): 엔드포인트·테이블 칸·화면 버튼 표가 문서에 빠짐없이 있는지."""

from pathlib import Path

import pytest

from scripts import docs_check


def test_docs_match_code() -> None:
    assert docs_check.api_problems() == []
    assert docs_check.erd_problems() == []
    assert docs_check.screen_problems() == []


def test_path_names_are_ignored() -> None:
    assert docs_check.normalize("/review/evaluations/{evaluation_id}/assign") == "/review/evaluations/{}/assign"
    assert docs_check.normalize("/review?tab=all") == "/review"


def test_missing_endpoint_is_reported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """API 명세에서 한 줄을 지우면 점검이 잡아낸다 (점검이 헛돌지 않음)."""
    text = docs_check.API_SPEC.read_text(encoding="utf-8")
    line = next(line for line in text.splitlines() if line.startswith("| S17 |"))
    spec = tmp_path / "API_Spec.md"
    spec.write_text(text.replace(line + "\n", ""), encoding="utf-8")
    monkeypatch.setattr(docs_check, "API_SPEC", spec)
    assert any("/student/requests/{}/delete" in p for p in docs_check.api_problems())


def test_missing_column_is_reported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    text = docs_check.ERD.read_text(encoding="utf-8")
    erd = tmp_path / "ERD.md"
    erd.write_text(text.replace("admission_year", "입학연도"), encoding="utf-8")
    monkeypatch.setattr(docs_check, "ERD", erd)
    assert "ERD users 절에 없는 칸: admission_year" in docs_check.erd_problems()
