# 공개 데모(예시용) 이미지: Hugging Face Spaces(Docker) 등 컨테이너 하나만 띄우는 곳에 올린다.
# 컨테이너 안에 MariaDB를 함께 띄우고, 예시 AI(Claude 미사용)·로컬 파일 저장·작업 즉시 실행으로 돌린다.
# 데이터는 컨테이너를 다시 시작하면 처음 상태로 돌아간다. 운영 배포에는 쓰지 않는다 (운영은 저장소 루트 Dockerfile).
FROM mariadb:11.8
COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /bin/uv
# 베이스(Ubuntu 24.04)의 Python 3.12를 쓴다
RUN apt-get update && apt-get install -y --no-install-recommends python3 && rm -rf /var/lib/apt/lists/*
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-group dev
COPY . .
# Hugging Face Spaces는 컨테이너를 사용자 id 1000으로 실행한다
RUN useradd -m -u 1000 demo 2>/dev/null || true; chown -R 1000:1000 /app /opt/venv
USER 1000
ENV DEMO_MODE=true \
    CELERY_TASK_ALWAYS_EAGER=true \
    CLAUDE_MODEL=demo-ai \
    APP_ENV=demo \
    DATABASE_URL="mysql+pymysql://creditbridge:demo@127.0.0.1:3306/creditbridge?charset=utf8mb4" \
    DEMO_STORAGE_DIR=/tmp/creditbridge-files \
    PORT=7860
EXPOSE 7860
ENTRYPOINT []
CMD ["sh", "deploy/huggingface/start.sh"]
