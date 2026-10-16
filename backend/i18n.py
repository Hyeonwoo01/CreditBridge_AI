"""화면 언어 (한국어·영어). 원문은 한국어이고, 영어는 backend/locales/en.json에서 한국어 원문을 열쇠로 찾는다.

- 요청마다 언어를 정한다(backend/main.py 미들웨어): cb_lang 쿠키 → 브라우저 Accept-Language → 한국어.
  로그인하면 users.locale을 쿠키로 옮기고, 화면 위 언어 전환(POST /lang)은 둘 다 바꾼다.
- 파이썬은 gettext("판정할 심사 {n}건", n=3), 템플릿은 {{ _("…", n=3) }}. 자리표시자는 str.format의 {이름}.
  영어 번역이 [단수, 복수] 목록이면 n 값으로 고른다.
- DB에 저장하는 글(알림, 분석 경고·오류)은 N_()로 표시한 한국어 원문 그대로 저장하고, 화면(| t)·메일에서
  translate_stored로 보는 사람(받는 사람 users.locale)의 언어로 바꾼다.
- 번역이 없으면 한국어 원문을 그대로 쓴다.
"""

import json
import re
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from functools import cache
from pathlib import Path
from typing import Any

from markupsafe import Markup, escape

LOCALES = ("ko", "en")
DEFAULT = "ko"
COOKIE = "cb_lang"
LABELS = {"ko": "한국어", "en": "English"}
CATALOG_DIR = Path(__file__).resolve().parent / "locales"

_current: ContextVar[str] = ContextVar("locale", default=DEFAULT)


@cache
def catalog(locale: str) -> dict[str, str | list[str]]:
    path = CATALOG_DIR / f"{locale}.json"
    if locale == DEFAULT or not path.exists():
        return {}
    data: dict[str, str | list[str]] = json.loads(path.read_text(encoding="utf-8"))
    return data


def normalize(value: str | None) -> str | None:
    """'en-US', 'EN' → 'en'. 지원하지 않으면 None."""
    if not value:
        return None
    code = value.strip().lower().replace("_", "-").split("-")[0]
    return code if code in LOCALES else None


def from_accept_language(header: str | None) -> str | None:
    """Accept-Language에서 가장 앞선(q가 큰) 지원 언어."""
    best: tuple[float, str] | None = None
    for i, part in enumerate((header or "").split(",")):
        lang, _, q = part.strip().partition(";q=")
        code = normalize(lang)
        if code is None:
            continue
        try:
            weight = float(q) if q else 1.0
        except ValueError:
            weight = 0.0
        key = (weight - i * 1e-6, code)
        if best is None or key > best:
            best = key
    return best[1] if best else None


def get_locale() -> str:
    return _current.get()


def set_locale(locale: str | None) -> None:
    _current.set(normalize(locale) or DEFAULT)


@contextmanager
def use_locale(locale: str | None) -> Iterator[None]:
    token = _current.set(normalize(locale) or DEFAULT)
    try:
        yield
    finally:
        _current.reset(token)


def _template(message: str, params: dict[str, Any]) -> str:
    locale = _current.get()
    if locale == DEFAULT:
        return message
    text = catalog(locale).get(message, message)
    if isinstance(text, list):
        # 단수·복수는 n 값으로, 없으면 첫 번째 정수 값으로 고른다
        n = params.get("n", next((v for v in params.values() if isinstance(v, int) and not isinstance(v, bool)), None))
        text = text[0] if n == 1 or len(text) == 1 else text[-1]
    return text


def gettext(message: str, /, **params: Any) -> str:
    """현재 언어로 바꾼 글. params가 있으면 {이름} 자리에 넣는다."""
    text = _template(message, params)
    return text.format(**params) if params else text


_ = gettext


def gettext_markup(message: str, /, **params: Any) -> Markup:
    """템플릿용: 글은 이스케이프하고, Markup으로 넘긴 값(매크로 결과 등)만 HTML 그대로 넣는다."""
    text = escape(_template(message, params))
    return text.format(**params) if params else text


def N_(message: str) -> str:
    """저장할 글의 한국어 원문 표시 (번역하지 않고 그대로 돌려준다). 화면에 보일 때 translate_stored가 번역한다.
    번역 목록 점검(tests/unit/test_i18n.py)이 이 표시로 저장용 원문을 모은다."""
    return message


@cache
def _patterns(locale: str) -> list[tuple[re.Pattern[str], str]]:
    """자리표시자가 있는 원문 → 저장된 글에서 값을 다시 뽑는 정규식."""
    out = []
    for key in catalog(locale):
        if "{" not in key:
            continue
        parts = re.split(r"\{(\w+)\}", key)
        regex, names = "", set()
        for i, part in enumerate(parts):
            if i % 2 == 0:
                regex += re.escape(part)
            elif part in names:
                regex += f"(?P={part})"
            else:
                names.add(part)
                regex += f"(?P<{part}>.*?)"
        out.append((re.compile(regex + r"\Z", re.S), key))
    # 글자가 많이 고정된 원문부터 (짧은 원문이 먼저 맞아 버리지 않게)
    out.sort(key=lambda item: -len(re.sub(r"\{\w+\}", "", item[1])))
    return out


def translate_stored(text: str, depth: int = 0) -> str:
    """DB에 한국어로 저장된 글(알림, 분석 경고·오류 메시지, 고정 항목)을 현재 언어로. 모르는 글은 그대로."""
    locale = _current.get()
    if locale == DEFAULT or not text or depth > 2:
        return text
    found = catalog(locale).get(text)
    if found is not None:
        return found if isinstance(found, str) else found[-1]
    # 여러 글을 " · "로 이은 경우(기한 알림 등): 조각마다 번역되면 조각별로
    if " · " in text:
        pieces = text.split(" · ")
        done = [translate_stored(p, depth + 1) for p in pieces]
        if all(a != b for a, b in zip(done, pieces, strict=True)):
            return " · ".join(done)
    for regex, key in _patterns(locale):
        m = regex.match(text)
        if m:
            params = {k: translate_stored(v, depth + 1) for k, v in m.groupdict().items()}
            return gettext(key, **{k: _number(v) for k, v in params.items()})
    return text


def _number(value: str) -> Any:
    """'1' → 1 (영어 단수·복수 고르기용)."""
    return int(value) if value.isdigit() else value
