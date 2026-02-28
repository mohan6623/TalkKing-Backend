.PHONY: dev test test-cov lint fmt fmt-check type-check \
        docker-build docker-up docker-down docker-logs \
        worker flower deploy-staging

# ── Python path ───────────────────────────────────────────────
PYTHON   := python
PYTEST   := pytest
UVICORN  := uvicorn

# ── Dev server ────────────────────────────────────────────────
dev:
	$(UVICORN) app.main:app --reload --host 127.0.0.1 --port 8000

# ── Tests ─────────────────────────────────────────────────────
test:
	$(PYTEST) tests/ -v --tb=short

test-cov:
	$(PYTEST) tests/ -v --tb=short \
	  --cov=app \
	  --cov-report=term-missing \
	  --cov-report=html:htmlcov \
	  --cov-fail-under=70

# ── Lint / Format ─────────────────────────────────────────────
lint:
	ruff check app/ tests/

fmt:
	ruff format app/ tests/

fmt-check:
	ruff format app/ tests/ --check

type-check:
	mypy app/ --ignore-missing-imports --no-strict-optional

# ── Docker ───────────────────────────────────────────────────
docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f --tail=100

worker:
	celery --app app.tasks.celery_app.celery_app worker \
	  --loglevel=info --concurrency=2 --queues=analysis

flower:
	celery --app app.tasks.celery_app.celery_app flower \
	  --port=5555

# ── Install ───────────────────────────────────────────────────
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

