#!/bin/sh
# 공개 데모 컨테이너 시작: 미리 만든 DB로 PostgreSQL(컨테이너 안)을 띄우고 웹 서버를 연다.
# 무료 호스팅(CPU 0.1개, 메모리 512MB)에 맞춰 PostgreSQL을 작게 띄우고(build_db.sh의 설정), 시작할 때 하는 일을 최소로 둔다.
set -e
DATA="${DEMO_DB_DIR:-/app/demo-db}"
# 이미지에 미리 만든 DB가 없으면(예: 빌드 단계를 건너뛴 환경) 지금 만든다
if [ ! -f "$DATA/PG_VERSION" ]; then
  sh deploy/demo/build_db.sh
fi
# 데이터 폴더 권한이 넓으면 PostgreSQL이 시작을 거부한다 (호스팅이 권한을 바꿔 놓는 경우 대비)
chmod 700 "$DATA"
pg_ctl -D "$DATA" -l /tmp/postgres.log -w -t 120 start >/dev/null || { cat /tmp/postgres.log; exit 1; }
# 세션 서명 키는 시작할 때마다 새로 만든다 (데모라 다시 시작하면 로그인이 풀려도 된다)
export SESSION_SECRET="${SESSION_SECRET:-$(od -An -tx1 -N32 /dev/urandom | tr -d ' \n')}"
# 호스팅이 정해 주는 PORT로 연다 (Hugging Face 7860, Render 10000 등).
# fastapi CLI 대신 uvicorn을 바로 띄워 메모리를 아낀다 (앞단 프록시의 https 정보는 그대로 받는다)
exec python -m uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-7860}" \
  --proxy-headers --forwarded-allow-ips='*' --no-access-log
