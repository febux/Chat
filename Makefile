# =============================================================================
#  FastAPIChat Makefile — run `make` or `make help` for the command list.
#
#  Conventions:
#    * A `## comment` after any target is shown automatically by `make help`.
#    * Any `?=` variable can be overridden on the CLI, e.g.
#         make test PYTEST_ARGS="-k users"
#         make db.migrate msg="add contact table"
# =============================================================================
SHELL := /bin/bash
.DEFAULT_GOAL := help

# --- Paths / identity --------------------------------------------------------
CWD := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
ME  := $(shell whoami)

# --- Configurable tools (override with VAR=value) ----------------------------
# pytest MUST run via the backend member-venv interpreter: the `src/` tree is a
# namespace package resolved relative to the repo root, so isolated runners
# (`uvx pytest`, `uv run`) cannot import fastapi/app modules.
PY          ?= src/backend/.venv/bin/python
PYTEST      ?= $(PY) -m pytest
PYTEST_ARGS ?=
SRC_DIR     ?= src

# docker compose shorthand (was repeated on every db/* target)
COMPOSE     ?= docker compose -f docker-compose.yaml
# Build the manager image and run a one-off alembic command inside it.
ALEMBIC     := $(COMPOSE) build manager && $(COMPOSE) run --rm --no-deps manager alembic

# Expose .env values to recipes that reference them as Make variables only.
# NOT exported (no `export` directive) so e.g. `make test` keeps a clean env.
ifneq (,$(wildcard .env))
  include .env
endif

# --- Fail fast if a required tool is missing (checked at parse time) ---------
REQUIRED_BINS := uv docker
$(foreach bin,$(REQUIRED_BINS),\
  $(if $(shell command -v $(bin) 2>/dev/null),,\
    $(error Required tool "$(bin)" is not installed or not on PATH)))

# --- All phony targets in one place ------------------------------------------
.PHONY: help \
        project.fix_own project.sync.clean project.sync project.install \
        project.doc-string project.docs-gen project.compile-deps \
        black-check black-format isort ruff-check ruff-format \
        bandit pysentry test mypy pyright typecheck pre-commit \
        lint format check clean clean.docker \
        db.upgrade db.migrate db.downgrade db.alembic-shell \
        db.local.upgrade db.local.migrate db.local.downgrade db.local.alembic-shell \
        up up.local startup startup.local \
        down down.volumes logs ps restart shell db.shell health \
        confirm

# =============================================================================
#  Help — auto-generated from `## ` comments (trick #1)
# =============================================================================
help: ## Show this help message
	@printf "FastAPIChat — available targets\n"
	@printf "Usage: make <target> [VAR=value ...]\n\n"
	@awk 'BEGIN {FS = ":.*## "} \
	     /^[a-zA-Z0-9_.%-]+:.*?## / \
	       {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}' \
	     $(MAKEFILE_LIST)

### Project -------------------------------------------------------------------
project.fix_own: ## Fix ownership of the migrations/ folder (needs sudo)
	@echo "me: $(ME)"
	sudo chown $(ME):$(ME) -R ./migrations

project.sync.clean: ## Sync the venv WITHOUT dev dependencies
	uv sync -U --no-dev

project.sync: ## Sync the project virtual environment
	uv sync -U

project.install: ## Install dependencies + pre-commit hooks
	pre-commit && \
	pre-commit install --hook-type pre-commit --hook-type pre-push

project.doc-string: ## Check doc-string coverage (interrogate)
	interrogate -c pyproject.toml src

project.docs-gen: ## Build the Sphinx HTML documentation
	uvx sphinx-build -M html docs/source/ docs/build/

project.compile-deps: ## Compile pinned requirements.txt from pyproject.toml
	uv pip compile pyproject.toml -o requirements.txt

### Linters & formatters ------------------------------------------------------
black-check: ## Check formatting with black
	uvx black src --check

black-format: ## Format code with black
	uvx black src

isort: ## Sort imports with isort
	uvx isort src

ruff-check: ## Lint with ruff
	uvx ruff check src

ruff-format: ## Auto-fix with ruff
	uvx ruff check src --fix

bandit: ## Scan for common security issues (bandit)
	bandit -r -c pyproject.toml .

pysentry: ## Audit installed Python libraries (pysentry)
	uvx pysentry-rs ./

mypy: ## Static type-check with mypy
	uvx mypy src

pyright: ## Static type-check with pyright
	uvx pyright

ty:
	uvx ty check src/backend

typecheck: mypy pyright ## Run mypy + pyright

pre-commit: ## Run every pre-commit hook across all files
	pre-commit run --all-files

lint: isort ruff-check bandit pysentry ## Run all linters

format: isort ruff-format ## Format the whole codebase

### Tests ---------------------------------------------------------------------
test: ## Run the test suite (member-venv interpreter, from repo root)
	$(PYTEST) $(PYTEST_ARGS)

check: lint test ## Full pre-push gate: lint, then test

### Cleanup -------------------------------------------------------------------
clean: ## Remove Python caches and local build artifacts
	@find . -type d \( -name __pycache__ -o -name .pytest_cache -o -name .ruff_cache \
		-o -name .mypy_cache -o -name .ipynb_checkpoints \) -prune -exec rm -rf {} +
	@rm -rf docs/build .coverage *.egg-info

clean.docker: ## Remove stopped service containers + dangling images (keeps volumes)
	-$(COMPOSE) rm -f -s
	-docker image prune -f

### Database (Alembic via the compose `manager` service) ----------------------
# `db.local.*` targets are kept as aliases of `db.*` — they behaved identically
# before (same compose command), so they now simply forward. Split them apart
# later if a local override compose file is introduced.
msg ?= Upgrade database tables

db.upgrade: ## Apply all migrations (alembic upgrade head)
	$(ALEMBIC) upgrade head
db.local.upgrade: db.upgrade ## (alias) Apply migrations — same as db.upgrade

db.migrate: ## Create a revision: make db.migrate msg="add contact table"
	$(ALEMBIC) revision --autogenerate -m "$(msg)"
db.local.migrate: db.migrate ## (alias) Create a migration — same as db.migrate

db.downgrade: ## Roll back the last migration (alembic downgrade -1)
	$(ALEMBIC) downgrade -1
db.local.downgrade: db.downgrade ## (alias) Roll back — same as db.downgrade

db.alembic-shell: ## Run any alembic cmd: make db.alembic-shell cmd="current"
	$(ALEMBIC) $(cmd)
db.local.alembic-shell: db.alembic-shell ## (alias) Alembic shell — same as db.alembic-shell

### Application (docker compose) ----------------------------------------------
up: ## Build & start backend + frontend (detached)
	$(COMPOSE) up --remove-orphans --build -d backend frontend

up.local: ## Build & start the FULL local stack (db, redis, nats, centrifugo, ...)
	$(COMPOSE) up --remove-orphans --build -d \
		backend frontend redis nats centrifugo db

startup: up db.upgrade ## Start core services, then apply migrations
startup.local: up.local db.local.upgrade ## Start the full stack, then apply migrations

down: ## Stop and remove containers (keeps named volumes / data)
	$(COMPOSE) down

down.volumes: confirm ## Stop & REMOVE containers + named volumes (data loss!)
	$(COMPOSE) down -v

logs: ## Tail logs from all services (Ctrl-C to exit)
	$(COMPOSE) logs -f --tail=100

ps: ## Show running compose containers
	$(COMPOSE) ps

restart: ## Restart backend + frontend
	$(COMPOSE) restart backend frontend

shell: ## Open a bash shell inside the backend container
	$(COMPOSE) exec backend bash

db.shell: ## Open a psql shell inside the db container
	$(COMPOSE) exec db psql -U "$(DATABASE_USER)" -d "$(DATABASE_SCHEMA)"

health: ## Hit the backend healthcheck endpoint
	@curl -fsS "http://localhost:$(SERVER_EXTERNAL_PORT)/api/v1/healthcheck" \
		&& printf "  -> OK\n" || (printf "  -> FAIL\n"; exit 1)

### Safety guards (used as prerequisites by other targets) --------------------
confirm: ## Prompt y/N confirmation (internal — used by destructive targets)
	@echo -n "Are you sure? [y/N] " && read ans && [ "$${ans:-N}" = y ]

guard-%: ## Require a variable: make guard-DATABASE_URL ...
	@if [ -z '$($*)' ]; then echo "ERROR: variable '$*' is not set"; exit 1; fi
