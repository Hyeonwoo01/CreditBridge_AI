import pymupdf
import pytest

from backend.documents.text import extract, validate_upload
from backend.errors import UploadRejectedError


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


def test_image_upload_becomes_a_page_to_transcribe() -> None:
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 20, 20), False)
    png = pix.tobytes("png")
    assert validate_upload("scan.png", png, max_mb=20) == ".png"
    doc = extract(png, "scan.png")
    assert doc.text == "" and len(doc.scanned_pages) == 1


@pytest.mark.parametrize(
    ("name", "data", "message"),
    [
        ("a.exe", b"MZ", "지원하지 않는 형식"),
        ("syllabus.docx", b"PK\x03\x04 docx", "PDF로 저장해서"),
        ("syllabus.txt", b"Week 1: Limits", "지원하지 않는 형식"),
        ("broken.png", b"not an image", "이미지를 열 수 없어요"),
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
        validate_upload("a.pdf", b"x" * (20 * 1024 * 1024 + 1), max_mb=20)
