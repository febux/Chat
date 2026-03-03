# Stage 1: Builder
FROM ghcr.io/astral-sh/uv:python3.14-bookworm AS dependencies
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Disable Python downloads, because we want to use the system interpreter
# across both images. If using a managed Python version, it needs to be
# copied from the build image into the final image; see `standalone.Dockerfile`
# for an example.
ENV UV_PYTHON_DOWNLOADS=0
RUN groupadd --gid 1001 appuser \
    && useradd --uid 1001 --gid 1001 --create-home appuser
USER appuser

WORKDIR /app
COPY --chown=appuser:appuser uv.lock pyproject.toml /app/
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev


# Stage 2: Production Image
# Then, use a final image without uv
FROM python:3.14-slim-bookworm AS builder

LABEL org.opencontainers.image.title="BaseAPIProject" \
      org.opencontainers.image.description="Production image for BaseAPIProject built with uvicorn" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.authors="Alexander Dedkov <alexd@betzo.net>" \
      org.opencontainers.image.licenses="MIT"

WORKDIR /app
RUN groupadd --gid 1001 appuser \
    && useradd --uid 1001 --gid 1001 --create-home appuser
RUN mkdir -p /app/logs /app/tmp && chmod 1777 /app/tmp && chown -R appuser:appuser /app

ENV TMPDIR=/app/tmp
ENV GUNICORN_CMD_ARGS="--worker-tmp-dir /app/tmp"
# Copy the application from the builder
COPY --from=dependencies --chown=appuser:appuser /app /app
RUN apt-get update && apt-get install -y --no-install-recommends wget curl logrotate

COPY --chown=appuser:appuser src ./src
COPY --chown=appuser:appuser config ./config

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"
USER appuser
