FROM python:3.15-slim-trixie

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Use the image's own Python (it matches the .python-version pin), never a
# uv-downloaded one.
ENV UV_PYTHON_PREFERENCE=only-system \
    UV_PYTHON_DOWNLOADS=never

RUN useradd -m -u 1000 app

WORKDIR /app

COPY pyproject.toml uv.lock .python-version README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ src/
RUN uv sync --frozen --no-dev && chown -R app:app /app

USER app

EXPOSE 8000

CMD [".venv/bin/uvicorn", "grid_emissions_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
