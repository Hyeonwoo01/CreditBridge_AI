"""decision course snapshot

결정 스냅샷 재현 (리뷰 v3 P0-8). 판정 때의 대상 과목(코드·이름·학점·학과), 출신 과목(코드·이름·학점·출신 대학),
환산 규칙(비율·방법·단위), 추천 규칙 버전을 decisions.course_snapshot에 남긴다. 판정 뒤 카탈로그나 규칙이 바뀌어도
내보내기·리포트가 판정 때 값을 그대로 보여 준다. 기존 판정은 판정 때 값을 알 수 없어 비워 둔다(지금 카탈로그로
채우면 사실과 다를 수 있음) — 읽는 쪽은 비어 있으면 지금 카탈로그 값을 쓴다.

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-11 06:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("decisions", sa.Column("course_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("decisions", "course_snapshot")
