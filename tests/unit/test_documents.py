import io
import zipfile

import pymupdf
import pytest

from app.documents.text import extract, validate_upload
from app.errors import UploadRejectedError


def make_pdf(pages: list[str], password: str | None = None) -> bytes:
    doc = pymupdf.open()
    for text in pages:
        page = doc.new_page()
        if text:
            page.insert_text((72, 72), text)
    kwargs = {"encryption": pymupdf.PDF_ENCRYPT_AES_256, "user_pw": password, "owner_pw": password} if password else {}
    data: bytes = doc.tobytes(**kwargs)
    return data


def test_pdf_text_layer_and_scanned_page_split() -> None:
    data = make_pdf(["Week 1: Limits and continuity of functions in calculus", ""])
    doc = extract(data, "s.pdf")
    assert "Limits and continuity" in doc.text
    assert len(doc.scanned_pages) == 1 and doc.quality == 0.5


def test_docx_and_txt() -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "word/document.xml",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
            "<w:p><w:r><w:t>Week 1: Vectors</w:t></w:r></w:p>"
            "<w:p><w:r><w:t>Week 2: Matrices</w:t></w:r></w:p></w:body></w:document>",
        )
    assert extract(buf.getvalue(), "a.docx").text == "Week 1: Vectors\nWeek 2: Matrices"
    assert extract("주차 1: 극한".encode("cp949"), "a.txt").text == "주차 1: 극한"


@pytest.mark.parametrize(
    ("name", "data", "message"),
    [
        ("a.exe", b"MZ", "지원하지 않는 형식"),
        ("a.pdf", b"   ", "빈 파일"),
        ("a.pdf", b"%PDF-broken", "PDF를 열 수 없어요"),
    ],
)
def test_rejects_with_reason(name: str, data: bytes, message: str) -> None:
    with pytest.raises(UploadRejectedError, match=message):
        validate_upload(name, data, max_mb=20)


def test_rejects_encrypted_and_oversized() -> None:
    with pytest.raises(UploadRejectedError, match="암호"):
        validate_upload("a.pdf", make_pdf(["secret"], password="pw"), max_mb=20)
    with pytest.raises(UploadRejectedError, match="20MB"):
        validate_upload("a.txt", b"x" * (20 * 1024 * 1024 + 1), max_mb=20)
