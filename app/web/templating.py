from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape

from app.security.csrf import csrf_token
from app.services.decisions import REASON_HINTS, REASON_LABELS

TEMPLATES = Jinja2Templates(directory=Path(__file__).parent / "templates")

REC_LABEL = {"direct": "직접 인정", "elective": "선택 인정", "none": "불인정", "insufficient": "정보 부족"}
CONF_LABEL = {"high": "상", "medium": "중", "low": "하"}
STATUS_LABEL = {"taught": "다룸", "partial": "부분", "not_taught": "없음", "unclear": "판단 불가"}
LEVEL_LABEL = {"same": "같은 수준", "lower": "낮은 수준", "higher": "높은 수준"}
FIELD_LABEL = {
    "learning_outcomes": "학습 목표",
    "weekly_topics": "주차별 주제",
    "textbooks": "교재",
    "prerequisites": "선수과목",
    "assessment": "평가 방식",
    "credits": "학점·시수",
}
ACTION_LABEL = {"approve": "승인", "modify": "수정", "reject": "반려"}
APPEAL_LABEL = {"submitted": "접수됨", "accepted": "재판정 중", "dismissed": "기각", "redecided": "재판정 완료"}
PRIVACY_LABEL = {"requested": "요청됨", "reviewed": "심사관 처리 완료 · 승인 대기", "completed": "삭제 완료"}


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


def pct(value: float | None) -> str:
    return "–" if value is None else f"{round(value * 100)}%"


def iso(value: datetime | None) -> str:
    return "" if value is None else value.isoformat(timespec="seconds") + "Z"


TEMPLATES.env.filters.update(
    rec=lambda v: REC_LABEL.get(v or "", "분석 중"),
    conf=lambda v: CONF_LABEL.get(v or "", "–"),
    concept_status=lambda v: STATUS_LABEL.get(v or "", v),
    level=lambda v: LEVEL_LABEL.get(v or "", v),
    field=lambda v: FIELD_LABEL.get(v, v),
    action=lambda v: ACTION_LABEL.get(v, v),
    pct=pct,
    iso=iso,
    reason=lambda v: REASON_LABELS.get(v, v),
    highlight=highlight,
    appeal_status=lambda v: APPEAL_LABEL.get(v, v),
    privacy_status=lambda v: PRIVACY_LABEL.get(v, v),
)
TEMPLATES.env.globals["reason_labels"] = REASON_LABELS
TEMPLATES.env.globals["reason_hints"] = REASON_HINTS


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
