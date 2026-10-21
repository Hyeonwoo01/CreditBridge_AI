FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-group dev
COPY . .
EXPOSE 8000
# root가 아닌 사용자로 실행한다 (앱이 뚫려도 컨테이너 안 권한을 좁힌다)
RUN useradd --create-home --uid 10001 app && chown -R app:app /app
USER app
CMD ["sh", "scripts/start.sh"]
