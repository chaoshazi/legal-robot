.PHONY: dev test migrate seed lint clean

dev:
	@echo "Starting dev environment..."
	docker compose up -d postgres qdrant
	cd backend && uvicorn app.main:app --reload --port 8000 &

test:
	cd backend && pytest -v

migrate:
	cd backend && alembic upgrade head

migration:
	cd backend && alembic revision --autogenerate -m "$(msg)"

seed:
	cd backend && python scripts/seed.py

lint:
	cd backend && ruff check .
	cd frontend && npx eslint src/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf frontend/dist
