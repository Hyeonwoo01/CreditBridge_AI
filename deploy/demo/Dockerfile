# 공개 데모(예시용) 이미지: Render 무료 웹 서비스, Hugging Face Spaces(Docker) 등 컨테이너 하나만 띄우는 곳에 올린다.
# 컨테이너 안에 PostgreSQL을 함께 띄우고, 예시 AI(Claude 미사용)·로컬 파일 저장·작업 즉시 실행으로 돌린다.
# 데이터는 컨테이너를 다시 시작하면 처음 상태로 돌아간다. 운영 배포에는 쓰지 않는다 (운영은 저장소 루트 Dockerfile).
# 공식 PostgreSQL 17 이미지(Debian bookworm)에 같은 bookworm용 공식 Python 3.12를 옮겨 담는다 (apt 설치 없음)
FROM postgres:17-bookworm
COPY --from=python:3.12-slim-bookworm /usr/local/bin/ /usr/local/bin/
COPY --from=python:3.12-slim-bookworm /usr/local/lib/ /usr/local/lib/
COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /bin/uv
RUN ldconfig
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:/usr/lib/postgresql/17/bin:$PATH
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-group dev
COPY . .
# Hugging Face Spaces는 컨테이너를 사용자 id 1000으로 실행한다 (Render도 이 사용자로 실행)
RUN useradd -m -u 1000 demo 2>/dev/null || true; chown -R 1000:1000 /app /opt/venv
USER 1000
ENV DEMO_MODE=true \
    CELERY_TASK_ALWAYS_EAGER=true \
    CLAUDE_MODEL=demo-ai \
    APP_ENV=demo \
    DATABASE_URL="postgresql+psycopg://creditbridge:demo@127.0.0.1:5432/creditbridge" \
    DEMO_DB_DIR=/app/demo-db \
    DEMO_STORAGE_DIR=/app/demo-files \
    MALLOC_ARENA_MAX=2 \
    PORT=7860
# 데모 DB·예시 시나리오·업로드 파일을 빌드할 때 미리 만든다 (시작을 빠르게, 다시 시작하면 이 상태로)
RUN sh deploy/demo/build_db.sh
EXPOSE 7860
ENTRYPOINT []
CMD ["sh", "deploy/demo/start.sh"]
