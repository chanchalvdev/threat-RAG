.PHONY: setup dev test lint ingest docker-up docker-down typecheck

BACKEND=backend
WEB=web

setup:
	cd $(BACKEND) && python -m venv .venv && \
	.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
	cd $(WEB) && npm install

dev:
	cd $(BACKEND) && .venv/bin/uvicorn app.main:app --reload --port 8000

dev-web:
	cd $(WEB) && npm run dev

test:
	cd $(BACKEND) && .venv/bin/pytest tests/unit -v --cov=app --cov-report=term-missing

test-integration:
	cd $(BACKEND) && .venv/bin/pytest tests/integration -v -m integration

lint:
	cd $(BACKEND) && .venv/bin/ruff check app/
	cd $(WEB) && npm run lint

typecheck:
	cd $(BACKEND) && .venv/bin/mypy app/ --ignore-missing-imports
	cd $(WEB) && npm run typecheck

ingest:
	cd $(BACKEND) && .venv/bin/python -m app.scripts.ingest_all

docker-up:
	docker compose -f infra/docker-compose.yml up -d

docker-down:
	docker compose -f infra/docker-compose.yml down

migrate:
	cd $(BACKEND) && .venv/bin/python -m app.scripts.migrate

validate: lint typecheck test
	@echo "All validation checks passed."

pull-models:
	curl -X POST http://localhost:11434/api/pull -d '{"name":"nomic-embed-text"}'
