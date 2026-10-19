#!/bin/sh
# 공개 데모 컨테이너 시작: 미리 만든 DB로 MariaDB(컨테이너 안)를 띄우고 웹 서버를 연다.
# 무료 호스팅(CPU 0.1개, 메모리 512MB)에 맞춰 MariaDB를 작게 띄우고, 시작할 때 하는 일을 최소로 둔다.
set -e
DATA="${DEMO_DB_DIR:-/app/demo-db}"
SOCK=/tmp/mariadb.sock
# 이미지에 미리 만든 DB가 없으면(예: 빌드 단계를 건너뛴 환경) 지금 만든다
if [ ! -d "$DATA/creditbridge" ]; then
  sh deploy/demo/build_db.sh
fi
mariadbd --datadir="$DATA" --socket="$SOCK" --bind-address=127.0.0.1 --port=3306 \
  --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci --skip-log-bin \
  --skip-name-resolve --performance-schema=OFF --innodb-buffer-pool-size=32M --innodb-log-buffer-size=4M \
  --key-buffer-size=4M --max-connections=20 --table-open-cache=200 --thread-cache-size=4 &
for i in $(seq 1 120); do
  if mariadb-admin --socket="$SOCK" -uroot ping >/dev/null 2>&1; then break; fi
  sleep 1
done
# 세션 서명 키는 시작할 때마다 새로 만든다 (데모라 다시 시작하면 로그인이 풀려도 된다)
export SESSION_SECRET="${SESSION_SECRET:-$(od -An -tx1 -N32 /dev/urandom | tr -d ' \n')}"
# 호스팅이 정해 주는 PORT로 연다 (Hugging Face 7860, Render 10000 등)
exec fastapi run backend/main.py --host 0.0.0.0 --port "${PORT:-7860}"
