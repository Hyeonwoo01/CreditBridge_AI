"""CSV 가져오기 공통 처리: 파일 검사, 인코딩(UTF-8·cp949), 필수 열 확인.

엑셀 파일은 'CSV UTF-8'로 저장해 올린다(엑셀 라이브러리를 추가하지 않는다).
각 가져오기는 한 줄이라도 틀리면 아무것도 저장하지 않는다.
"""

import csv
import io
from collections.abc import Iterator

from backend.errors import CreditBridgeError
from backend.i18n import gettext as tr

MAX_BYTES = 5 * 1024 * 1024


def _decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "cp949"):  # 한국어 엑셀의 기본 CSV 인코딩까지
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise CreditBridgeError(tr("CSV 파일의 인코딩을 읽을 수 없어요. 'CSV UTF-8'로 저장해 올려 주세요."))


def read_rows(
    filename: str, data: bytes, columns: list[str], required: list[str], max_rows: int
) -> Iterator[tuple[int, dict[str, str]]]:
    """(행 번호, 앞뒤 공백을 지운 값) 을 돌려준다. 빈 줄은 건너뛴다. 행 번호는 엑셀과 같게 머리 줄이 1행."""
    if not filename.lower().endswith(".csv"):
        raise CreditBridgeError(
            tr("CSV 파일만 올릴 수 있어요. 엑셀에서 '다른 이름으로 저장 → CSV UTF-8'을 골라 주세요.")
        )
    if not data.strip():
        raise CreditBridgeError(tr("빈 파일이에요."))
    if len(data) > MAX_BYTES:
        raise CreditBridgeError(tr("파일이 5MB를 넘어요. 나눠서 올려 주세요."))
    reader = csv.DictReader(io.StringIO(_decode(data)))
    missing = [c for c in required if c not in (reader.fieldnames or [])]
    if missing:
        raise CreditBridgeError(
            tr(
                "필수 열이 없어요: {missing}. 첫 줄은 {columns} 이어야 해요.",
                missing=", ".join(missing),
                columns=", ".join(columns),
            )
        )
    for count, raw in enumerate(reader, start=1):
        if count > max_rows:
            raise CreditBridgeError(
                tr("한 번에 {max_rows}줄까지만 가져올 수 있어요. 나눠서 올려 주세요.", max_rows=max_rows)
            )
        row = {k.strip(): (v or "").strip() for k, v in raw.items() if k}
        if any(row.values()):
            yield reader.line_num, row  # 빈 줄까지 센 실제 줄 번호 (엑셀 행 번호와 같다)
