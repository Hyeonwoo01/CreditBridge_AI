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
# 악용 방지: PDF 쪽수 상한, AI로 전사하는 스캔 페이지 수 상한(쪽마다 AI 호출), 이미지 픽셀 상한(메모리)
MAX_PAGES = 60
MAX_SCANNED_PAGES = 20
MAX_PIXELS = 25_000_000
RENDER_DPI = 150


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
            if doc.page_count > MAX_PAGES:
                raise UploadRejectedError(
                    tr("PDF가 {pages}쪽을 넘어요. 필요한 쪽만 남겨 올려 주세요.", pages=MAX_PAGES)
                )
    else:
        # 픽셀 수를 머리말에서 먼저 확인한다: 작은 파일이 거대한 이미지로 풀려 메모리를 다 쓰지 않게
        size = image_size(data)
        if size is None:
            raise UploadRejectedError(tr("이미지를 열 수 없어요. JPG 또는 PNG 파일인지 확인해 주세요."))
        if size[0] * size[1] > MAX_PIXELS:
            raise UploadRejectedError(tr("이미지 해상도가 너무 커요. 크기를 줄여서 올려 주세요."))
        try:
            pymupdf.Pixmap(data)
        except Exception as exc:
            raise UploadRejectedError(tr("이미지를 열 수 없어요. JPG 또는 PNG 파일인지 확인해 주세요.")) from exc
    return ext


_JPEG_SOF = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}


def image_size(data: bytes) -> tuple[int, int] | None:
    """PNG·JPEG 머리말에서 (가로, 세로) 픽셀을 읽는다. 알 수 없으면 None."""
    if data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR":
        return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    if data[:2] != b"\xff\xd8":
        return None
    i = 2
    while i + 4 <= len(data):
        if data[i] != 0xFF:
            return None
        marker = data[i + 1]
        if marker == 0xFF:  # 채움 바이트
            i += 1
            continue
        if marker in (0x01, 0xD8) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        length = int.from_bytes(data[i + 2 : i + 4], "big")
        if marker in _JPEG_SOF and i + 9 <= len(data):
            return int.from_bytes(data[i + 7 : i + 9], "big"), int.from_bytes(data[i + 5 : i + 7], "big")
        if length < 2:
            return None
        i += 2 + length
    return None


def _render(page: pymupdf.Page) -> bytes:
    """스캔 페이지를 이미지로. 쪽 크기가 비정상적으로 크면 배율을 낮춰 MAX_PIXELS를 넘지 않게 한다."""
    zoom = RENDER_DPI / 72
    area = max(page.rect.width * page.rect.height, 1.0)
    zoom = min(zoom, (MAX_PIXELS / area) ** 0.5)
    return page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).tobytes("png")


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
            elif len(scanned) < MAX_SCANNED_PAGES:
                scanned.append(_render(page))
                scanned_index.append(number)
                pages.append("")
            else:
                pages.append(text)  # 전사 상한을 넘은 스캔 페이지는 AI에 보내지 않는다
        total = len(doc)
    quality = (total - len(scanned)) / total if total else 0.0
    return ExtractedDocument(
        text="\n".join(pages), quality=quality, scanned_pages=scanned, pages=pages, scanned_index=scanned_index
    )
