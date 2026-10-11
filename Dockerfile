FROM debian:trixie-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# There is no official python:3.15-slim image yet (only release candidates),
# so uv installs the Python that .python-version pins. /opt/python keeps it
# readable for the non-root app user.
ENV UV_PYTHON_INSTALL_DIR=/opt/python \
    UV_PYTHON_PREFERENCE=only-managed

RUN useradd -m -u 1000 app

WORKDIR /app

COPY pyproject.toml uv.lock .python-version README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ src/
RUN uv sync --frozen --no-dev && chown -R app:app /app

USER app

EXPOSE 8000

CMD [".venv/bin/uvicorn", "grid_emissions_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
