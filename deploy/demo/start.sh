#!/bin/sh
# 공개 데모 컨테이너 시작: MariaDB(컨테이너 안) → 마이그레이션 → 데모 데이터·예시 시나리오 → 웹 서버
# 무료 호스팅(메모리 512MB)에 맞춰 MariaDB를 작게 띄운다
set -e
DATA=/tmp/mariadb
SOCK=/tmp/mariadb.sock
if [ ! -d "$DATA/mysql" ]; then
  mariadb-install-db --datadir="$DATA" --auth-root-authentication-method=normal --skip-test-db >/dev/null
fi
mariadbd --datadir="$DATA" --socket="$SOCK" --bind-address=127.0.0.1 --port=3306 \
  --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci --skip-log-bin \
  --skip-name-resolve --performance-schema=OFF --innodb-buffer-pool-size=32M --innodb-log-buffer-size=4M \
  --key-buffer-size=4M --max-connections=20 --table-open-cache=200 --thread-cache-size=4 &
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
alembic upgrade head
python -m scripts.demo_scenario
# 호스팅이 정해 주는 PORT로 연다 (Hugging Face 7860, Render 10000 등)
exec fastapi run backend/main.py --host 0.0.0.0 --port "${PORT:-7860}"
