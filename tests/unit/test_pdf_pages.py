"""FR-25 원본 PDF 페이지 위치표와 판정 근거 리포트 PDF 만들기."""

import pymupdf

from backend.documents.pdf import html_to_pdf
from backend.documents.text import extract, join_pages, page_at
from backend.services.analysis import document_to_text
from tests.fakes import FakeLLM
from tests.unit.test_documents import make_pdf


def test_page_offsets_map_positions_to_pages() -> None:
    text, offsets = join_pages(["abc", "", "de"])
    assert text == "abc\n\nde" and offsets == [0, 4, 5, 7]
    assert [page_at(offsets, i) for i in range(len(text))] == [1, 1, 1, 1, 2, 3, 3]
    assert page_at(offsets, len(text)) is None  # 원본 밖(보완 자료로 덧붙인 글)
    assert page_at(None, 0) is None and page_at([], 0) is None


def test_scanned_page_transcription_stays_in_its_page() -> None:
    long = "Course overview and grading policy for the first part of the semester."
    data = make_pdf(["", long])  # 1쪽 스캔본, 2쪽 텍스트
    doc = extract(data, "s.pdf")
    assert doc.scanned_index == [0] and doc.pages[0] == ""

    result = document_to_text(FakeLLM(), data, "s.pdf")  # type: ignore[arg-type]
    assert result.text.index("Week 1: Limits") < result.text.index("Course overview")  # 전사 글이 1쪽 자리에
    assert page_at(result.page_offsets, result.text.index("Derivatives")) == 1
    assert page_at(result.page_offsets, result.text.index("grading policy")) == 2


def test_report_pdf_keeps_korean_text_and_page_numbers() -> None:
    html = "<h1>판정 근거 리포트</h1>" + "<p>결과 직접 인정 · MATH 1151 Calculus I</p>" * 120
    data = html_to_pdf(html, title="report", footer="AI는 추천만 하고 최종 판정은 학과 교수가 합니다.")
    doc = pymupdf.open("pdf", data)
    assert len(doc) >= 2 and doc.metadata is not None and doc.metadata["title"] == "report"
    first = doc[0].get_text()
    assert "판정 근거 리포트" in first and "MATH 1151" in first and f"1 / {len(doc)}" in first
    assert "최종 판정은 학과 교수" in doc[len(doc) - 1].get_text()
    assert len(data) < 500_000  # 글꼴은 쓴 글자만 넣는다
