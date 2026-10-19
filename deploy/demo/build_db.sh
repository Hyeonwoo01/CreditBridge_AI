#!/bin/sh
# 데모 DB와 예시 시나리오를 미리 만들어 둔다. 이미지를 빌드할 때 한 번 실행한다 (무료 호스팅은 CPU가 작아
# 시작할 때마다 만들면 2~3분 걸리고 그동안 502가 난다). 컨테이너를 다시 시작하면 이 상태로 돌아간다.
set -e
DATA="${DEMO_DB_DIR:-/app/demo-db}"
SOCK=/tmp/mariadb-build.sock
mariadb-install-db --datadir="$DATA" --auth-root-authentication-method=normal --skip-test-db >/dev/null
mariadbd --datadir="$DATA" --socket="$SOCK" --bind-address=127.0.0.1 --port=3306 --skip-log-bin \
  --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci --performance-schema=OFF &
for i in $(seq 1 60); do
  if mariadb-admin --socket="$SOCK" -uroot ping >/dev/null 2>&1; then break; fi
  sleep 1
done
mariadb --socket="$SOCK" -uroot -e "
  CREATE DATABASE IF NOT EXISTS creditbridge CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
  CREATE USER IF NOT EXISTS 'creditbridge'@'127.0.0.1' IDENTIFIED BY 'demo';
  GRANT ALL ON creditbridge.* TO 'creditbridge'@'127.0.0.1';"
SESSION_SECRET=build alembic upgrade head
SESSION_SECRET=build python -m scripts.demo_scenario
mariadb-admin --socket="$SOCK" -uroot shutdown
wait
