from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape

from backend.i18n import LABELS, LOCALES, N_, get_locale, gettext, gettext_markup, translate_stored
from backend.security.csrf import csrf_token
from backend.services.decisions import REASON_HINTS, REASON_LABELS

TEMPLATES = Jinja2Templates(directory=Path(__file__).resolve().parents[2] / "frontend" / "templates")

REC_LABEL = {
    "direct": N_("직접 인정"),
    "elective": N_("선택 인정"),
    "none": N_("불인정"),
    "insufficient": N_("정보 부족"),
}
CONF_LABEL = {"high": N_("상"), "medium": N_("중"), "low": N_("하")}
STATUS_LABEL = {"taught": N_("다룸"), "partial": N_("부분"), "not_taught": N_("없음"), "unclear": N_("판단 불가")}
LEVEL_LABEL = {"same": N_("같은 수준"), "lower": N_("낮은 수준"), "higher": N_("높은 수준")}
FIELD_LABEL = {
    "learning_outcomes": N_("학습 목표"),
    "weekly_topics": N_("주차별 주제"),
    "textbooks": N_("교재"),
    "prerequisites": N_("선수과목"),
    "assessment": N_("평가 방식"),
    "credits": N_("학점·시수"),
}
ACTION_LABEL = {"approve": N_("승인"), "modify": N_("수정"), "reject": N_("반려")}
APPEAL_LABEL = {
    "submitted": N_("접수됨"),
    "accepted": N_("재판정 중"),
    "dismissed": N_("기각"),
    "redecided": N_("재판정 완료"),
}
PRIVACY_LABEL = {
    "requested": N_("요청됨"),
    "reviewed": N_("심사관 처리 완료 · 승인 대기"),
    "completed": N_("삭제 완료"),
}


def highlight(text: str, marks: list[tuple[int, int]], prefix: str) -> Markup:
    """원문에 근거 구절을 표시한다. 구절마다 시작 위치에 이동용 앵커(#prefix-시작-끝)를 둔다 (FR-25)."""
    valid = sorted({(s, e) for s, e in marks if 0 <= s < e <= len(text)})
    merged: list[list[int]] = []
    for s, e in valid:
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    anchors: dict[int, list[str]] = {}
    for s, e in valid:
        anchors.setdefault(s, []).append(f'<span id="{prefix}-{s}-{e}" class="scroll-mt-28"></span>')
    out: list[str] = []
    pos = 0
    points = sorted({0, len(text), *anchors, *(m[0] for m in merged), *(m[1] for m in merged)})
    open_until = -1
    for point in points:
        if point > pos:
            out.append(str(escape(text[pos:point])))
            pos = point
        if point == open_until:
            out.append("</mark>")
            open_until = -1
        out.extend(anchors.get(point, []))
        start = next((m for m in merged if m[0] == point), None)
        if start is not None:
            out.append("<mark>")
            open_until = start[1]
    return Markup("".join(out))


def ai_text(obj: Any, field: str, fallback: str = "") -> str:
    """AI가 쓴 설명을 화면 언어로: 영어 화면이면 field_en(있을 때), 아니면 한국어 field.
    evaluation-v1 결과처럼 영어가 없으면 한국어를 그대로 보여 준다."""
    if obj is None:
        return fallback
    value = getattr(obj, field, "") or fallback
    if get_locale() != "ko":
        english = getattr(obj, f"{field}_en", "")
        if english:
            return str(english)
    return str(value)


def ai_list(obj: Any, field: str) -> list[str]:
    """AI가 쓴 목록(보완 자료 등)을 화면 언어로. 영어 목록이 없으면 한국어(고정 항목은 | t로 번역)."""
    items: list[str] = list(getattr(obj, field, []) or [])
    english: list[str] = list(getattr(obj, f"{field}_en", []) or [])
    if get_locale() != "ko" and english and len(english) == len(items):
        return english
    return [translate_stored(i) for i in items]


def ai_item(item: str, obj: Any, field: str = "missing_materials") -> str:
    """AI가 제안한 항목 하나(보완 자료 요청에 저장된 값 등)를 화면 언어로: 같은 분석의 영어 목록에서 짝을 찾는다."""
    if get_locale() != "ko" and obj is not None:
        items: list[str] = list(getattr(obj, field, []) or [])
        english: list[str] = list(getattr(obj, f"{field}_en", []) or [])
        if item in items and len(english) == len(items):
            return english[items.index(item)]
    return translate_stored(item)


def ai_warnings(result: Any) -> list[str]:
    """분석 경고: AI가 쓴 경고는 영어 사본, 고정 문구는 번역 목록으로."""
    english: list[str] = list(getattr(result, "warnings_en", []) or [])
    out = []
    for i, warning in enumerate(getattr(result, "warnings", []) or []):
        en = english[i] if i < len(english) else ""
        out.append(en if get_locale() != "ko" and en else translate_stored(warning))
    return out


def pct(value: float | None) -> str:
    return "–" if value is None else f"{round(value * 100)}%"


def iso(value: datetime | None) -> str:
    return "" if value is None else value.isoformat(timespec="seconds") + "Z"


def utc(value: datetime | None) -> str:
    """PDF처럼 브라우저가 시각을 바꿔 주지 않는 곳에 쓰는 UTC 표기."""
    return "–" if value is None else value.strftime("%Y-%m-%d %H:%M") + " UTC"


def _label(table: Mapping[Any, str], value: str | None, default: str | None = None) -> str:
    """코드값의 화면 이름을 현재 언어로 (모르는 값은 그대로)."""
    text = table.get(value or "", default if default is not None else (value or ""))
    return gettext(text) if text else text


TEMPLATES.env.filters.update(
    rec=lambda v: _label(REC_LABEL, v, N_("분석 중")),
    conf=lambda v: _label(CONF_LABEL, v, "–"),
    concept_status=lambda v: _label(STATUS_LABEL, v),
    level=lambda v: _label(LEVEL_LABEL, v),
    field=lambda v: _label(FIELD_LABEL, v),
    action=lambda v: _label(ACTION_LABEL, v),
    pct=pct,
    iso=iso,
    utc=utc,
    reason=lambda v: _label(REASON_LABELS, v),
    highlight=highlight,
    appeal_status=lambda v: _label(APPEAL_LABEL, v),
    privacy_status=lambda v: _label(PRIVACY_LABEL, v),
    t=lambda v: translate_stored(v) if isinstance(v, str) else v,  # DB에 한국어로 저장된 글 번역
    ai=ai_text,
    ai_list=ai_list,
    ai_warnings=ai_warnings,
    ai_item=ai_item,
)
TEMPLATES.env.globals.update(
    reason_labels=REASON_LABELS,
    reason_hints=REASON_HINTS,
    _=gettext_markup,
    tr=gettext,  # 이스케이프하지 않은 글 (JSON 등)
    current_locale=get_locale,
    locales=LOCALES,
    locale_labels=LABELS,
)


def render(request: Request, name: str, status_code: int = 200, **context: Any) -> Response:
    flashes = request.session.pop("flash", []) if "session" in request.scope else []
    response: Response = TEMPLATES.TemplateResponse(
        request,
        name,
        {"flashes": flashes, "csrf_token": csrf_token(request) if "session" in request.scope else "", **context},
        status_code=status_code,
    )
    return response


def flash(request: Request, message: str, kind: str = "info") -> None:
    request.session.setdefault("flash", []).append({"message": message, "kind": kind})
