from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates

from app.security.csrf import csrf_token

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
