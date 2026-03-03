# Stage 1: Builder
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Disable Python downloads, because we want to use the system interpreter
# across both images. If using a managed Python version, it needs to be
# copied from the build image into the final image; see `standalone.Dockerfile`
# for an example.
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /app
COPY uv.lock pyproject.toml /app/
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev


# Stage 2: Production Image
# Then, use a final image without uv
FROM python:3.14-slim-bookworm

WORKDIR /app
# Copy the application from the builder
COPY --from=builder /app /app

COPY migrations ./migrations
COPY alembic.ini src/app/main.py ./
COPY src ./src
COPY config ./config

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"


