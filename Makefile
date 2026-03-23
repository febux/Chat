SHELL := /bin/bash
CWD := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
ME := $(shell whoami)

#include .env


help:
	@echo "- up: Start the application in development mode"
	@echo "- test: Run the test suite"
	@echo "- lint: Run linters (ruff, black, isort)"
	@echo "- format: Format the code using black and isort"
	@echo "- check: Run all checks (linting, formatting, and tests)"
	@echo "- clean: Remove all generated files"
	@echo "- fix_own: Fix permissions for the current user for migrations folder"
	@echo "- project.sync.clean: Sync the project virtual environment cleanly, without dev libs"
	@echo "- project.sync: Sync the project virtual environment"
	@echo "- project.install: Install pre-commit hooks and dependencies"
	@echo "- project.doc-string: Generate documentation strings"
	@echo "- project.docs-gen: Generate documentation"
	@echo "- project.compile-deps: Compile dependencies"
	@echo "- black-check: Check if the code is black-formatted"
	@echo "- black-format: Format the code using black"
	@echo "- isort: Sort imports using isort"
	@echo "- interrogate: Generate documentation strings using interrogate"
	@echo "- ruff: Check if the code is ruff-formatted"
	@echo "- ruff-format: Format the code using ruff"
	@echo "- bandit: Check for common security vulnerabilities using bandit"
	@echo "- pysentry: Security audit python libraries"
	@echo "- mypy: Check for type errors using mypy"
	@echo "- pyright: Check for type errors using pyright"
	@echo "- db.local.downgrade: Alembic downgrade local"
	@echo "- db.local.upgrade: Alembic upgrade local"
	@echo "- db.local.migrate: Alembic migrate local"
	@echo "- db.local.alembic-shell: Alembic shell local"
	@echo "- db.downgrade: Alembic downgrade"
	@echo "- db.upgrade: Alembic upgrade"
	@echo "- db.migrate: Alembic migrate"
	@echo "- db.alembic-shell: Alembic shell"



### Common commands
project.fix_own:
	@echo "me: $(ME)"
	sudo chown $(ME):$(ME) -R ./migrations


### Project commands
project.sync.clean:
	uv sync -U --no-dev

project.sync:
	uv sync -U

project.install:
	pre-commit && \
	pre-commit install --hook-type pre-commit --hook-type pre-push

project.doc-string:
	interrogate -c pyproject.toml src

project.docs-gen:
	uvx sphinx-build -M html docs/source/ docs/build/

project.compile-deps:
	uv pip compile pyproject.toml -o requirements.txt


### Linters commands
black-check:
	uvx black src --check

black-format:
	uvx black src

isort:
	uvx isort src

ruff-check:
	uvx ruff check src

ruff-format:
	uvx ruff check src --fix

bandit:
	bandit -r -c pyproject.toml -r .

pysentry:
	uvx pysentry-rs ./

test:
	uvx pytest

mypy:
	uvx mypy src

pyright:
	uvx pyright

lint: isort black-check ruff-check bandit pysentry

format: isort black-format ruff-format bandit pysentry

check: lint test

# Database commands
msg?="Upgrade database tables"

db.local.downgrade:
	docker compose -f docker-compose.yaml build manager && \
	docker compose -f docker-compose.yaml run --rm --no-deps manager alembic downgrade -1

db.local.migrate:
	docker compose -f docker-compose.yaml build manager && \
	docker compose -f docker-compose.yaml run --rm --no-deps manager alembic revision --autogenerate -m $(msg)

db.local.upgrade:
	docker compose -f docker-compose.yaml build manager && \
	docker compose -f docker-compose.yaml run --rm --no-deps manager alembic upgrade head

db.local.alembic-shell:
	docker compose -f docker-compose.yaml build manager && \
	docker compose -f docker-compose.yaml run --rm --no-deps manager alembic $(cmd)

db.downgrade:
	docker compose -f docker-compose.yaml build manager && \
	docker compose -f docker-compose.yaml run --rm --no-deps manager alembic downgrade -1

db.migrate:
	docker compose -f docker-compose.yaml build manager && \
	docker compose -f docker-compose.yaml run --rm --no-deps manager alembic revision --autogenerate -m $(msg)

db.upgrade:
	docker compose -f docker-compose.yaml build manager && \
	docker compose -f docker-compose.yaml run --rm --no-deps manager alembic upgrade head

db.alembic-shell:
	docker compose -f docker-compose.yaml build manager && \
	docker compose -f docker-compose.yaml run --rm --no-deps manager alembic $(cmd)

### Application commands
up.local:
	docker compose up --remove-orphans --build -d \
		backend \
		frontend \
		redis \
		nats \
		centrifugo \
		db

up:
	docker compose up --remove-orphans --build -d \
		backend \
		frontend

startup.local: up.local db.local.upgrade

startup: up db.upgrade
