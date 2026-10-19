#!/bin/sh
# db/init.sql(스키마)과 db/data.sql(초기 데이터)을 다시 만든다.
# 스키마(Alembic 마이그레이션)나 데모 데이터(scripts/seed_demo.py)를 바꾸면 실행하고 결과를 함께 커밋한다.
#   준비: docker compose up -d db
#   실행: sh scripts/export_db_sql.sh
# 스키마의 기준은 Alembic이다. init.sql은 그 결과를 SQL로 옮긴 것이라 직접 고치지 않는다.
set -e
cd "$(dirname "$0")/.."
PG_EXEC="${PG_EXEC:-docker compose exec -T db}"
PG_USER="${PG_USER:-creditbridge}"
PG_PASSWORD="${PG_PASSWORD:-change-me}"
PG_HOST_PORT="${PG_HOST_PORT:-localhost:5432}"
SEED_DB=creditbridge_seed

# 1) init.sql: 마이그레이션을 SQL로 출력한다 (DB에 접속하지 않는다)
{
  echo "-- CreditBridge AI 스키마 (PostgreSQL). 자동 생성: sh scripts/export_db_sql.sh — 직접 고치지 말 것"
  echo "-- 기준: alembic/versions (alembic upgrade head --sql). alembic_version도 함께 만들어 앱의 마이그레이션과 이어진다"
  DATABASE_URL="postgresql+psycopg://$PG_USER@$PG_HOST_PORT/x" uv run --no-sync alembic upgrade head --sql 2>/dev/null
} > db/init.sql

# 2) data.sql: 빈 임시 DB에 마이그레이션과 데모 데이터를 넣고 데이터만 덤프한다
$PG_EXEC psql -q -U "$PG_USER" -d postgres -c "DROP DATABASE IF EXISTS $SEED_DB" -c "CREATE DATABASE $SEED_DB"
SEED_URL="postgresql+psycopg://$PG_USER:$PG_PASSWORD@$PG_HOST_PORT/$SEED_DB"
DATABASE_URL="$SEED_URL" uv run --no-sync alembic upgrade head 2>/dev/null
DATABASE_URL="$SEED_URL" uv run --no-sync python -m scripts.seed_demo
{
  echo "-- CreditBridge AI 초기 데이터 (데모용 대상 대학·과목·기준 강의계획서·계정, 비밀번호 demo1234)."
  echo "-- 자동 생성: sh scripts/export_db_sql.sh (scripts/seed_demo.py 결과를 pg_dump) — 직접 고치지 말 것. 운영 DB에는 넣지 않는다"
  $PG_EXEC pg_dump -U "$PG_USER" -d "$SEED_DB" --data-only --inserts --column-inserts --disable-triggers \
    --exclude-table=alembic_version --no-owner --no-privileges --restrict-key=creditbridge
} > db/data.sql
$PG_EXEC psql -q -U "$PG_USER" -d postgres -c "DROP DATABASE $SEED_DB"
echo "db/init.sql, db/data.sql 갱신 완료"
