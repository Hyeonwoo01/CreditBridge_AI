#!/bin/sh
# 데모 DB와 예시 시나리오를 미리 만들어 둔다. 이미지를 빌드할 때 한 번 실행한다 (무료 호스팅은 CPU가 작아
# 시작할 때마다 만들면 2~3분 걸리고 그동안 502가 난다). 컨테이너를 다시 시작하면 이 상태로 돌아간다.
set -e
DATA="${DEMO_DB_DIR:-/app/demo-db}"
PWFILE=$(mktemp)
echo demo > "$PWFILE"
initdb -D "$DATA" -U creditbridge --pwfile="$PWFILE" --auth=scram-sha-256 -E UTF8 --locale=C.UTF-8 >/dev/null
rm -f "$PWFILE"
# 메모리를 작게 쓰는 설정 (시작할 때도 이 파일을 그대로 쓴다)
cat >> "$DATA/postgresql.conf" <<CONF
listen_addresses = '127.0.0.1'
port = 5432
unix_socket_directories = '/tmp'
max_connections = 15
shared_buffers = 16MB
work_mem = 2MB
maintenance_work_mem = 16MB
wal_buffers = 512kB
max_wal_size = 64MB
min_wal_size = 32MB
max_worker_processes = 2
max_parallel_workers = 0
max_parallel_workers_per_gather = 0
autovacuum_max_workers = 1
fsync = off
synchronous_commit = off
full_page_writes = off
logging_collector = off
log_min_messages = warning
CONF
pg_ctl -D "$DATA" -l /tmp/postgres-build.log -w start >/dev/null || { cat /tmp/postgres-build.log; exit 1; }
PGPASSWORD=demo createdb -h 127.0.0.1 -U creditbridge creditbridge
SESSION_SECRET=build alembic upgrade head
SESSION_SECRET=build python -m scripts.demo_scenario
pg_ctl -D "$DATA" -m fast -w stop >/dev/null
