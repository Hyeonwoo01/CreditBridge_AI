"""업로드 문서 → 텍스트 (FR-01). PDF 텍스트 레이어는 PyMuPDF, 스캔본은 페이지 이미지로 넘겨 Claude가 전사한다."""

import io
import re
import zipfile
from dataclasses import dataclass, field
from xml.etree import ElementTree

import pymupdf

from app.errors import UploadRejectedError

ALLOWED = {".pdf", ".txt", ".md", ".docx", ".jpg", ".jpeg", ".png"}
CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/plain",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}
# 텍스트 레이어가 이보다 짧은 PDF 페이지는 스캔본으로 보고 이미지로 전사한다
MIN_PAGE_CHARS = 40
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


@dataclass
class ExtractedDocument:
    text: str
    # 텍스트 레이어가 있는 비율 0~1 (스캔본 전사 후 재계산)
    quality: float
    scanned_pages: list[bytes] = field(default_factory=list)


def extension(filename: str) -> str:
    match = re.search(r"\.[A-Za-z0-9]+$", filename)
    return match.group(0).lower() if match else ""


def validate_upload(filename: str, data: bytes, max_mb: int) -> str:
    """형식·크기·빈 파일을 검사하고 확장자를 돌려준다. 거부 사유는 사용자에게 그대로 보여준다."""
    ext = extension(filename)
    if ext not in ALLOWED:
        raise UploadRejectedError(
            f"지원하지 않는 형식이에요 ({ext or '확장자 없음'}). PDF, JPG·PNG, TXT, DOCX만 올릴 수 있어요."
        )
    if not data.strip():
        raise UploadRejectedError("빈 파일이에요. 내용이 있는 파일을 올려 주세요.")
    if len(data) > max_mb * 1024 * 1024:
        raise UploadRejectedError(f"파일이 {max_mb}MB를 넘어요.")
    if ext == ".pdf":
        try:
            doc = pymupdf.open(stream=data, filetype="pdf")
        except Exception as exc:
            raise UploadRejectedError("PDF를 열 수 없어요. 손상되지 않은 파일인지 확인해 주세요.") from exc
        with doc:
            if doc.needs_pass:
                raise UploadRejectedError("암호가 걸린 PDF예요. 암호를 해제한 뒤 올려 주세요.")
    return ext


def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "cp949", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _docx_text(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        root = ElementTree.fromstring(zf.read("word/document.xml"))
    paragraphs = []
    for p in root.iter(f"{_W}p"):
        paragraphs.append("".join(t.text or "" for t in p.iter(f"{_W}t")))
    return "\n".join(paragraphs)


def extract(data: bytes, filename: str) -> ExtractedDocument:
    ext = extension(filename)
    if ext in (".txt", ".md"):
        return ExtractedDocument(text=_decode(data), quality=1.0)
    if ext == ".docx":
        try:
            return ExtractedDocument(text=_docx_text(data), quality=1.0)
        except (KeyError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
            raise UploadRejectedError("DOCX 파일을 읽을 수 없어요.") from exc
    if ext in (".jpg", ".jpeg", ".png"):
        pix = pymupdf.Pixmap(data)
        return ExtractedDocument(text="", quality=0.0, scanned_pages=[pix.tobytes("png")])

    pages: list[str] = []
    scanned: list[bytes] = []
    with pymupdf.open(stream=data, filetype="pdf") as doc:
        for page in doc:
            text = page.get_text("text")
            if len(text.strip()) >= MIN_PAGE_CHARS:
                pages.append(text)
            else:
                scanned.append(page.get_pixmap(dpi=150).tobytes("png"))
                pages.append("")
        total = len(doc)
    quality = (total - len(scanned)) / total if total else 0.0
    return ExtractedDocument(text="\n".join(pages), quality=quality, scanned_pages=scanned)
