FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-group dev
COPY . .
EXPOSE 8000
CMD ["uv", "run", "--no-group", "dev", "fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]
