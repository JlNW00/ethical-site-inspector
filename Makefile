.PHONY: dev setup setup-backend setup-frontend lint test build clean

# Single command setup + run
dev: setup
	@echo "Starting backend and frontend..."
	@echo "Run 'cd backend && .venv/Scripts/activate && uvicorn app.main:app --reload' in one terminal"
	@echo "Run 'cd frontend && npm run dev' in another terminal"

setup: setup-backend setup-frontend

setup-backend:
	cd backend && python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt && .venv/Scripts/python -m alembic upgrade head

setup-frontend:
	cd frontend && npm install

lint:
	cd backend && ruff check app/
	cd backend && ruff format --check app/
	cd frontend && npm run lint
	cd frontend && npm run format:check

test:
	cd backend && pytest tests/ -v --tb=short --durations=10
	cd frontend && npm test

build:
	cd frontend && npm run build

typecheck:
	cd backend && mypy app/ --ignore-missing-imports
	cd frontend && npx tsc -b

clean:
	rm -rf backend/.venv frontend/node_modules frontend/dist
