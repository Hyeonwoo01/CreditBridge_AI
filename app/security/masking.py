"""성적표 개인식별정보 마스킹 (FR-13). LLM과 로그에는 마스킹된 텍스트만 넘긴다."""

import re
from dataclasses import dataclass

_NAME_LINE = re.compile(r"^(\s*(?:student\s+name|name|성명|이름)\s*[:：]\s*)(.+)$", re.I | re.M)
_ID_LINE = re.compile(r"^(\s*(?:student\s+(?:id|no\.?|number)|id\s+no\.?|학번)\s*[:：]\s*)(\S.*)$", re.I | re.M)
_DOB_LINE = re.compile(r"^(\s*(?:date\s+of\s+birth|birth\s*date|dob|생년월일)\s*[:：]\s*)(.+)$", re.I | re.M)
_RRN = re.compile(r"\b\d{6}\s*-\s*[1-4]\d{6}\b")
_LONG_DIGITS = re.compile(r"\b\d{8,10}\b")


@dataclass(frozen=True)
class MaskedText:
    text: str
    masked_name: str | None


def mask_name(name: str) -> str:
    return " ".join(part[0] + "*" * (len(part) - 1) if len(part) > 1 else "*" for part in name.split())


def mask_pii(text: str) -> MaskedText:
    name_match = _NAME_LINE.search(text)
    masked_name = mask_name(name_match.group(2).strip()) if name_match else None
    out = _NAME_LINE.sub(lambda m: m.group(1) + mask_name(m.group(2).strip()), text)
    out = _ID_LINE.sub(lambda m: m.group(1) + "[MASKED-ID]", out)
    out = _DOB_LINE.sub(lambda m: m.group(1) + "[MASKED-DOB]", out)
    out = _RRN.sub("[MASKED-RRN]", out)
    out = _LONG_DIGITS.sub("[MASKED-NUM]", out)
    return MaskedText(text=out, masked_name=masked_name)
