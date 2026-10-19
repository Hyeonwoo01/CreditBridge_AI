#!/bin/sh
# 공개 데모 컨테이너 시작: MariaDB(컨테이너 안) → 마이그레이션 → 데모 데이터·예시 시나리오 → 웹 서버
set -e
DATA=/tmp/mariadb
SOCK=/tmp/mariadb.sock
if [ ! -d "$DATA/mysql" ]; then
  mariadb-install-db --datadir="$DATA" --auth-root-authentication-method=normal --skip-test-db >/dev/null
fi
mariadbd --datadir="$DATA" --socket="$SOCK" --bind-address=127.0.0.1 --port=3306 \
  --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci --skip-log-bin &
for i in $(seq 1 60); do
  if mariadb-admin --socket="$SOCK" -uroot ping >/dev/null 2>&1; then break; fi
  sleep 1
done
mariadb --socket="$SOCK" -uroot -e "
  CREATE DATABASE IF NOT EXISTS creditbridge CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
  CREATE USER IF NOT EXISTS 'creditbridge'@'127.0.0.1' IDENTIFIED BY 'demo';
  GRANT ALL ON creditbridge.* TO 'creditbridge'@'127.0.0.1';"
# 세션 서명 키는 시작할 때마다 새로 만든다 (데모라 다시 시작하면 로그인이 풀려도 된다)
export SESSION_SECRET="${SESSION_SECRET:-$(od -An -tx1 -N32 /dev/urandom | tr -d ' \n')}"
uv run --no-sync alembic upgrade head
uv run --no-sync python -m scripts.demo_scenario
exec uv run --no-sync fastapi run backend/main.py --host 0.0.0.0 --port "${PORT:-7860}"
