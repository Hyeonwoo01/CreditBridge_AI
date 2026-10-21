"""erase closed appeal reasons

문서 삭제로 종료된 요청의 이의 신청 사유(학생이 쓴 글)를 지운다. 이제 삭제 승인 때 함께 지우므로,
이 변경 전에 이미 종료된 요청에도 같은 상태를 맞춘다. 스키마는 바뀌지 않는다.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-21 09:00:00
"""

from collections.abc import Sequence

from alembic import op


revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE appeals SET reason = ''
        WHERE reason <> '' AND course_evaluation_id IN (
            SELECT e.id FROM course_evaluations AS e
            JOIN transfer_requests AS r ON r.id = e.transfer_request_id
            WHERE r.status = 'closed'
        )
        """
    )


def downgrade() -> None:
    pass  # 지운 사유는 되돌릴 수 없다
