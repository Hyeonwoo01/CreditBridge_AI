"""db/init.sql이 Alembic 마이그레이션과 같은지 (스키마를 바꾸고 sh scripts/export_db_sql.sh를 잊으면 실패)."""

import io
import os
from pathlib import Path

from alembic.config import Config

from alembic import command

ROOT = Path(__file__).parent.parent.parent


def test_init_sql_matches_migrations() -> None:
    buffer = io.StringIO()
    cfg = Config(str(ROOT / "alembic.ini"), output_buffer=buffer)
    os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://creditbridge@localhost:5432/x")
    command.upgrade(cfg, "head", sql=True)

    def statements(text: str) -> list[str]:
        return [line for line in text.splitlines() if not line.startswith("-- ")]

    stored = statements((ROOT / "db/init.sql").read_text())
    assert stored == statements(buffer.getvalue()), "db/init.sql이 오래됐어요: sh scripts/export_db_sql.sh"


def test_data_sql_has_demo_accounts_and_no_schema() -> None:
    data = (ROOT / "db/data.sql").read_text()
    assert "INSERT INTO public.users" in data and "jiwon@student.example" in data
    assert "CREATE TABLE" not in data and "alembic_version" not in data
