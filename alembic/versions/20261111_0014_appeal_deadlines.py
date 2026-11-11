"""appeal deadlines

이의 신청 기한·처리 기한 (리뷰 v3 P1-5). 학칙 정책에 appeal_window(판정 뒤 이의 신청을 받는 일 수)와
appeal_review(접수 뒤 학사처 처리 기한 일 수)를 더하고, 이의 신청에 처리 기한(appeals.due_at)을 남긴다.
정책이 없으면 지금처럼 기한 없이 받는다. 기존 이의 신청의 처리 기한은 비워 둔다.

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-11 08:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD = "rule_type IN ('min_grade', 'transfer_cap', 'degree_credits', 'semester_load')"
NEW = (
    "rule_type IN ('min_grade', 'transfer_cap', 'degree_credits', 'semester_load', "
    "'appeal_window', 'appeal_review')"
)


def upgrade() -> None:
    op.add_column("appeals", sa.Column("due_at", sa.DateTime(), nullable=True))
    op.drop_constraint(op.f("ck_policy_rules_rule_type_valid"), "policy_rules", type_="check")
    op.create_check_constraint(op.f("ck_policy_rules_rule_type_valid"), "policy_rules", NEW)


def downgrade() -> None:
    op.execute("DELETE FROM policy_rules WHERE rule_type IN ('appeal_window', 'appeal_review')")
    op.drop_constraint(op.f("ck_policy_rules_rule_type_valid"), "policy_rules", type_="check")
    op.create_check_constraint(op.f("ck_policy_rules_rule_type_valid"), "policy_rules", OLD)
    op.drop_column("appeals", "due_at")
