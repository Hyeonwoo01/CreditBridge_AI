"""운영 비밀값 검사와 업로드 크기 제한 (작은 파일이 거대한 이미지·수많은 쪽으로 풀리는 것 방지)."""

import struct

import pymupdf
import pytest

from backend.config import Settings
from backend.documents import text as doc_text
from backend.errors import UploadRejectedError
from backend.services.csv_import import safe_cell


def test_production_rejects_example_secrets() -> None:
    with pytest.raises(ValueError):
        Settings(app_env="production", session_secret="change-me", database_url="postgresql+psycopg://u:p@h/db")
    with pytest.raises(ValueError):
        Settings(app_env="production", session_secret="x" * 40, database_url="postgresql+psycopg://u:change-me@h/db")
    ok = Settings(app_env="production", session_secret="x" * 40, database_url="postgresql+psycopg://u:p@h/db")
    assert ok.is_production
    assert Settings(app_env="local", session_secret="change-me").session_secret == "change-me"  # 로컬은 그대로


def test_image_pixel_bomb_and_page_cap_are_rejected() -> None:
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 40, 30), 0)
    png, jpg = pix.tobytes("png"), pix.tobytes("jpg")
    assert doc_text.image_size(png) == (40, 30) and doc_text.image_size(jpg) == (40, 30)
    bomb = png[:16] + struct.pack(">II", 20000, 20000) + png[24:]
    with pytest.raises(UploadRejectedError):
        doc_text.validate_upload("bomb.png", bomb, 20)
    pdf = pymupdf.open()
    for _ in range(doc_text.MAX_PAGES + 1):
        pdf.new_page()
    with pytest.raises(UploadRejectedError):
        doc_text.validate_upload("long.pdf", pdf.tobytes(), 20)


def test_scanned_pages_sent_to_ai_are_capped() -> None:
    pdf = pymupdf.open()
    for _ in range(doc_text.MAX_SCANNED_PAGES + 5):
        pdf.new_page()  # 글자 없는 쪽 = 스캔본으로 본다
    extracted = doc_text.extract(pdf.tobytes(), "scan.pdf")
    assert len(extracted.scanned_pages) == doc_text.MAX_SCANNED_PAGES


def test_csv_cells_starting_with_formula_chars_are_quoted() -> None:
    assert safe_cell("=1+1") == "'=1+1" and safe_cell("@SUM(A1)") == "'@SUM(A1)" and safe_cell("-2") == "'-2"
    assert safe_cell("MATH 101") == "MATH 101" and safe_cell(3) == 3
