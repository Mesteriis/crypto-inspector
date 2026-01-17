.PHONY: setup install run celery migrate migration docker-up docker-down docker-build lint test clean pre-commit pre-commit-install sync-requirements

# Local development setup
setup:
	cp -n .env.example .env || true
	uv sync
	$(MAKE) pre-commit-install

install:
	uv sync

install-dev:
	uv sync --all-extras

# Run application
run:
	PYTHONPATH=src uv run uvicorn main:app --reload

celery:
	PYTHONPATH=src uv run celery -A tasks.celery_app worker --loglevel=info

# Database migrations
migrate:
	PYTHONPATH=src uv run alembic upgrade head

migration:
	@read -p "Migration message: " msg; \
	PYTHONPATH=src uv run alembic revision --autogenerate -m "$$msg"

downgrade:
	PYTHONPATH=src uv run alembic downgrade -1

# Docker
docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-build:
	docker compose build

docker-logs:
	docker compose logs -f

# Code quality
lint:
	uv run ruff check src

lint-fix:
	uv run ruff check src --fix

format:
	uv run ruff format src

# Pre-commit hooks
pre-commit-install:
	uv run pre-commit install

pre-commit:
	uv run pre-commit run --all-files

sync-requirements:
	./scripts/sync-requirements.sh

test:
	PYTHONPATH=src uv run pytest

# Cleanup
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
