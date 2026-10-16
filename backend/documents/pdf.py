"""HTML → PDF (판정 근거 리포트 내려받기). PyMuPDF Story로 A4에 흘려 쓰고 쪽 번호를 붙인다.

한글이 섞여도 글꼴이 바뀌지 않게 PyMuPDF에 들어 있는 CJK 글꼴(Droid Sans Fallback) 하나로 쓰고,
PDF에는 쓴 글자만 넣는다(subset)."""

import io
from functools import cache
from pathlib import Path

import pymupdf

PAGE = pymupdf.paper_rect("a4")
BODY = pymupdf.Rect(48, 52, PAGE.width - 48, PAGE.height - 60)  # 여백 왼쪽·오른쪽 48pt, 위 52pt, 아래 60pt
MUTED = (0.478, 0.478, 0.478)  # DESIGN.md ink-muted-48 (#7a7a7a)

CSS = """
@font-face { font-family: cb; src: url(cb.ttf); }
* { font-family: cb; }
body { font-size: 9.5pt; line-height: 1.55; color: #1d1d1f; }
h1 { font-size: 17pt; margin: 6pt 0 2pt 0; }
h2 { font-size: 11.5pt; margin: 14pt 0 4pt 0; }
p { margin: 0 0 3pt 0; }
.muted { color: #7a7a7a; }
.reject { color: #c9302c; }
.label { font-size: 8pt; color: #0066cc; }
table { border-collapse: collapse; width: 100%; }
th { text-align: left; font-size: 8.5pt; color: #7a7a7a; border-bottom: 1px solid #e0e0e0; padding: 3pt 4pt; }
td { border-bottom: 1px solid #f0f0f0; padding: 3pt 4pt; vertical-align: top; }
.quote { margin: 0 0 2pt 10pt; }
"""


@cache
def _font() -> bytes:
    return bytes(pymupdf.Font("cjk").buffer)


def html_to_pdf(html: str, *, title: str, footer: str, assets: Path | None = None) -> bytes:
    """assets: <img src="파일이름">으로 쓸 이미지가 있는 폴더."""
    archive = pymupdf.Archive()
    archive.add(_font(), "cb.ttf")
    if assets is not None:
        archive.add(str(assets))
    story = pymupdf.Story(html, user_css=CSS, archive=archive)
    buffer = io.BytesIO()
    writer = pymupdf.DocumentWriter(buffer)
    more = 1
    while more:
        device = writer.begin_page(PAGE)
        more, _ = story.place(BODY)
        story.draw(device)
        writer.end_page()
    writer.close()

    doc = pymupdf.open("pdf", buffer.getvalue())
    total = len(doc)
    for number in range(1, total + 1):
        page = doc.load_page(number - 1)
        y = PAGE.height - 30
        page.insert_font(fontname="cb", fontbuffer=_font())
        page.insert_text((48, y), footer, fontsize=7.5, fontname="cb", color=MUTED)
        label = f"{number} / {total}"
        width = pymupdf.get_text_length(label, fontname="helv", fontsize=7.5)
        page.insert_text((PAGE.width - 48 - width, y), label, fontsize=7.5, fontname="helv", color=MUTED)
    doc.set_metadata({"title": title, "creator": "CreditBridge AI", "producer": "CreditBridge AI"})
    doc.subset_fonts()
    data: bytes = doc.tobytes(garbage=3, deflate=True)
    doc.close()
    return data
