"""llm usage

AI 호출 사용량 (리뷰 v3 13.7 비용 지표, H15). llm_usage: 백그라운드 작업 시도마다 (용도, 모델)별 호출 수와
입력·출력 토큰 합계. 관리자 콘솔 'AI 사용량'이 최근 7일을 모아 보여 준다. 기존 데이터는 없다(지금부터 쌓임).

Revision ID: 0020
Revises: 0019
Create Date: 2026-11-12 08:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "llm_usage",
        sa.Column("institution_id", sa.BigInteger(), nullable=True),
        sa.Column("job_id", sa.BigInteger(), nullable=True),
        sa.Column("purpose", sa.String(length=60), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("calls", sa.Integer(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["institution_id"], ["institutions.id"], name=op.f("fk_llm_usage_institution_id_institutions")
        ),
        sa.ForeignKeyConstraint(["job_id"], ["background_jobs.id"], name=op.f("fk_llm_usage_job_id_background_jobs")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_llm_usage")),
    )
    op.create_index("ix_llm_usage_institution_created", "llm_usage", ["institution_id", "created_at"], unique=False)
    op.create_index(op.f("ix_llm_usage_job_id"), "llm_usage", ["job_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_llm_usage_job_id"), table_name="llm_usage")
    op.drop_index("ix_llm_usage_institution_created", table_name="llm_usage")
    op.drop_table("llm_usage")
