"""scripts/demo_data/*.txt 강의계획서를 업로드용 PDF로 만든다. 실행: uv run python -m scripts.make_demo_pdfs"""

import textwrap
from pathlib import Path

import pymupdf

DEMO_DATA = Path(__file__).parent / "demo_data"
LINES_PER_PAGE = 48
WRAP_CHARS = 95  # A4 폭·10pt 기준. 긴 줄은 잘리지 않게 나눈다


def text_to_pdf(text: str) -> bytes:
    """한 줄씩 옮겨 텍스트 레이어가 있는 PDF를 만든다. 페이지 폭을 넘는 줄은 줄바꿈한다."""
    doc = pymupdf.open()
    lines = [part for line in text.splitlines() for part in (textwrap.wrap(line, WRAP_CHARS) or [""])] or [""]
    for start in range(0, len(lines), LINES_PER_PAGE):
        page = doc.new_page()
        y = 60.0
        for line in lines[start : start + LINES_PER_PAGE]:
            page.insert_text((56, y), line, fontsize=10, fontname="helv")
            y += 15
    data: bytes = doc.tobytes(no_new_id=True)  # 같은 텍스트면 같은 바이트 (내용 해시 재사용 시연)
    doc.close()
    return data


if __name__ == "__main__":
    for txt in sorted(DEMO_DATA.glob("*.txt")):
        txt.with_suffix(".pdf").write_bytes(text_to_pdf(txt.read_text(encoding="utf-8")))
        print("wrote", txt.with_suffix(".pdf").name)
