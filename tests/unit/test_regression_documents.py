"""문서 추출(OCR 경로)·개인정보 가림 회귀 (리뷰 v3 P0-8).

저장소에 있는 데모 PDF(scripts/demo_data/*.pdf)를 그대로 읽어 쪽 수·스캔 판정·품질·쪽 위치표·글 해시를
골든 파일(tests/fixtures/regression/extraction.json)과 비교한다. PyMuPDF를 올리거나 추출 코드를 바꿔 결과가
달라지면 여기서 드러난다. 의도한 변경이면 `REGEN_GOLDEN=1 uv run pytest tests/unit/test_regression_documents.py`로
다시 만들고 차이를 확인해 커밋한다. 실제 AI 전사(스캔본)는 API가 필요해 여기서는 자리 넣기만 확인한다.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pymupdf

from backend.documents import text as doc_text
from backend.security.masking import mask_pii
from backend.services.analysis import document_to_text
from tests.fakes import FakeLLM

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT / "scripts" / "demo_data"
GOLDEN = ROOT / "tests" / "fixtures" / "regression" / "extraction.json"


def summary(data: bytes, name: str) -> dict[str, Any]:
    doc = doc_text.extract(data, name)
    text, offsets = doc_text.join_pages(doc.pages)
    return {
        "pages": len(doc.pages),
        "scanned_index": doc.scanned_index,
        "quality": round(doc.quality, 3),
        "hidden": len(doc.hidden),
        "chars": len(text),
        "sha256": hashlib.sha256(text.encode()).hexdigest(),
        "first_line": text.strip().splitlines()[0] if text.strip() else "",
        "offsets": offsets,
    }


def mixed_pdf() -> bytes:
    """글 쪽 → 그림만 있는 스캔 쪽 → 글 쪽."""
    doc = pymupdf.open()
    doc.new_page().insert_text((50, 60), "Week 1: Sets and functions. " * 3, fontsize=10)
    scan = doc.new_page()
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 40, 40), False)
    pix.clear_with(200)
    scan.insert_image(scan.rect, pixmap=pix)
    doc.new_page().insert_text((50, 60), "Week 3: Relations and graphs. " * 3, fontsize=10)
    return doc.tobytes()


def current() -> dict[str, Any]:
    out: dict[str, Any] = {p.name: summary(p.read_bytes(), p.name) for p in sorted(DEMO.glob("*.pdf"))}
    out["mixed_scan.pdf"] = summary(mixed_pdf(), "mixed_scan.pdf")
    out["transcript_masked"] = mask_pii((DEMO / "transcript.txt").read_text("utf-8")).text
    return out


def test_extraction_matches_golden() -> None:
    now = current()
    if os.environ.get("REGEN_GOLDEN"):
        GOLDEN.write_text(json.dumps(now, ensure_ascii=False, indent=1) + "\n", "utf-8")
    golden = json.loads(GOLDEN.read_text("utf-8"))
    assert now.keys() == golden.keys()
    for name in golden:
        assert now[name] == golden[name], name


def test_scanned_page_is_transcribed_in_place() -> None:
    """스캔 쪽은 AI 전사 글이 원래 쪽 자리에 들어가고, 근거 위치→쪽 번호가 맞아야 한다."""
    llm = FakeLLM()
    result = document_to_text(llm, mixed_pdf(), "mixed_scan.pdf")
    pages = result.text.split("\n")
    assert "Week 1: Sets" in result.text and "Week 3: Relations" in result.text
    transcribed = result.text.index("Week 1: Limits")  # FakeLLM 전사 결과
    assert doc_text.page_at(result.page_offsets, transcribed) == 2
    assert doc_text.page_at(result.page_offsets, result.text.index("Week 3")) == 3
    assert len(llm.prompts("PageTranscription")) == 1  # 스캔 쪽만 AI로
    assert pages


def test_masking_never_leaks_identifiers() -> None:
    masked = current()["transcript_masked"]
    raw = (DEMO / "transcript.txt").read_text("utf-8")
    for line in raw.splitlines():
        key = line.split(":")[0].strip().lower() if ":" in line else ""
        if key in {"student name", "name", "성명", "이름", "student id", "학번", "date of birth", "생년월일"}:
            value = line.split(":", 1)[1].strip()
            assert value and value not in masked, key
