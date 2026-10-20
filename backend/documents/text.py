"""업로드 문서 → 텍스트 (FR-01). PDF와 스캔 이미지(JPG·PNG)만 받는다.
PDF 텍스트 레이어는 PyMuPDF로 읽고, 스캔 페이지와 이미지는 AI(Claude·GPT)가 전사한다."""

import re
from bisect import bisect_right
from dataclasses import dataclass, field

import pymupdf

from backend.errors import UploadRejectedError
from backend.i18n import gettext as tr

ALLOWED = {".pdf", ".jpg", ".jpeg", ".png"}
CONTENT_TYPES = {".pdf": "application/pdf", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
# 텍스트 레이어가 이보다 짧은 PDF 페이지는 스캔본으로 보고 이미지로 전사한다
MIN_PAGE_CHARS = 40


@dataclass
class ExtractedDocument:
    text: str
    # 텍스트 레이어가 있는 비율 0~1 (스캔본 전사 후 재계산)
    quality: float
    scanned_pages: list[bytes] = field(default_factory=list)
    # 페이지별 텍스트 (스캔 페이지는 ""), scanned_index는 scanned_pages 각각의 페이지 번호(0부터)
    pages: list[str] = field(default_factory=list)
    scanned_index: list[int] = field(default_factory=list)


def join_pages(pages: list[str]) -> tuple[str, list[int]]:
    """페이지 텍스트를 줄바꿈으로 잇고 페이지 위치표를 돌려준다 (FR-25 원본 PDF 페이지로 이동).

    위치표는 [1쪽 시작, 2쪽 시작, …, 마지막 쪽 끝]이라 페이지 수보다 하나 길다.
    끝 위치 뒤(보완 자료로 덧붙인 글)는 원본 파일의 페이지가 아니다."""
    offsets: list[int] = []
    pos = 0
    for i, page in enumerate(pages):
        offsets.append(pos)
        pos += len(page) + (1 if i < len(pages) - 1 else 0)
    offsets.append(pos)
    return "\n".join(pages), offsets


def page_at(offsets: list[int] | None, position: int) -> int | None:
    """원문 위치가 원본 파일의 몇 쪽(1부터)인지. 위치표가 없거나 원본 밖이면 None."""
    if not offsets or len(offsets) < 2 or not 0 <= position < offsets[-1]:
        return None
    return bisect_right(offsets, position, hi=len(offsets) - 1)


def extension(filename: str) -> str:
    match = re.search(r"\.[A-Za-z0-9]+$", filename)
    return match.group(0).lower() if match else ""


def validate_upload(filename: str, data: bytes, max_mb: int) -> str:
    """형식·크기·빈 파일을 검사하고 확장자를 돌려준다. 거부 사유는 사용자에게 그대로 보여준다."""
    ext = extension(filename)
    if ext not in ALLOWED:
        raise UploadRejectedError(
            tr(
                "지원하지 않는 형식이에요 ({ext}). PDF 또는 JPG·PNG 이미지만 올릴 수 있어요. "
                "DOCX 같은 문서는 PDF로 저장해서 올려 주세요.",
                ext=ext or tr("확장자 없음"),
            )
        )
    if not data.strip():
        raise UploadRejectedError(tr("빈 파일이에요. 내용이 있는 파일을 올려 주세요."))
    if len(data) > max_mb * 1024 * 1024:
        raise UploadRejectedError(tr("파일이 {mb}MB를 넘어요.", mb=max_mb))
    if ext == ".pdf":
        try:
            doc = pymupdf.open(stream=data, filetype="pdf")
        except Exception as exc:
            raise UploadRejectedError(tr("PDF를 열 수 없어요. 손상되지 않은 파일인지 확인해 주세요.")) from exc
        with doc:
            if doc.needs_pass:
                raise UploadRejectedError(tr("암호가 걸린 PDF예요. 암호를 해제한 뒤 올려 주세요."))
    else:
        try:
            pymupdf.Pixmap(data)
        except Exception as exc:
            raise UploadRejectedError(tr("이미지를 열 수 없어요. JPG 또는 PNG 파일인지 확인해 주세요.")) from exc
    return ext


def extract(data: bytes, filename: str) -> ExtractedDocument:
    ext = extension(filename)
    if ext in (".jpg", ".jpeg", ".png"):
        pix = pymupdf.Pixmap(data)
        return ExtractedDocument(
            text="", quality=0.0, scanned_pages=[pix.tobytes("png")], pages=[""], scanned_index=[0]
        )

    pages: list[str] = []
    scanned: list[bytes] = []
    scanned_index: list[int] = []
    with pymupdf.open(stream=data, filetype="pdf") as doc:
        for number, page in enumerate(doc):
            text = page.get_text("text")
            if len(text.strip()) >= MIN_PAGE_CHARS:
                pages.append(text)
            else:
                scanned.append(page.get_pixmap(dpi=150).tobytes("png"))
                scanned_index.append(number)
                pages.append("")
        total = len(doc)
    quality = (total - len(scanned)) / total if total else 0.0
    return ExtractedDocument(
        text="\n".join(pages), quality=quality, scanned_pages=scanned, pages=pages, scanned_index=scanned_index
    )
