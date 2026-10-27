.PHONY: lint test test-unit test-integration up down clean frontend-lint frontend-test

lint:
	cd backend && ruff check . && ruff format --check . && mypy --config-file pyproject.toml app
	cd frontend && npm run lint && npm run typecheck

test-unit:
	cd backend && pytest tests/unit -v

test-integration:
	cd backend && pytest tests/integration -v

test: test-unit test-integration
	cd frontend && npm test -- --run

up:
	docker compose up --build

down:
	docker compose down

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf backend/.pytest_cache backend/.mypy_cache frontend/dist
