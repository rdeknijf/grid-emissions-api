FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN useradd -m -u 1000 app

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ src/
RUN uv sync --frozen --no-dev && chown -R app:app /app

USER app

EXPOSE 8000

CMD [".venv/bin/uvicorn", "grid_emissions_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
