# InsightFlow v2 — Development Makefile
.PHONY: dev backend frontend install test lint migrate build help

# ── Setup ──────────────────────────────────────────────────────────────────────
install:
	@echo "📦 Installing backend dependencies..."
	cd backend && pip install -e ".[dev]" 2>/dev/null || pip install -r requirements.txt
	@echo "📦 Installing frontend dependencies..."
	cd frontend && npm install
	@echo "✅ Installation complete"

# ── Development ───────────────────────────────────────────────────────────────
dev:
	@echo "🚀 Starting InsightFlow dev environment..."
	@$(MAKE) -j2 backend frontend

backend:
	@echo "⚡ Starting FastAPI backend on :8000..."
	cd backend && uvicorn main:app --reload --port 8000 --host 0.0.0.0

frontend:
	@echo "⚡ Starting Vite frontend on :5173..."
	cd frontend && npm run dev

# ── Docker ────────────────────────────────────────────────────────────────────
docker-up:
	docker compose up -d postgres redis
	@echo "✅ PostgreSQL and Redis are up"

docker-down:
	docker compose down

docker-full:
	docker compose up --build

# ── Database ──────────────────────────────────────────────────────────────────
migrate:
	@echo "🗄️  Running Alembic migrations..."
	cd backend && alembic upgrade head

migrate-gen:
	@echo "🗄️  Generating new migration (provide MESSAGE= argument)..."
	cd backend && alembic revision --autogenerate -m "$(MESSAGE)"

migrate-down:
	cd backend && alembic downgrade -1

# ── Testing ───────────────────────────────────────────────────────────────────
test:
	@echo "🧪 Running all tests..."
	cd backend && pytest --cov=. --cov-report=term-missing -v

test-unit:
	cd backend && pytest tests/unit/ -v

test-integration:
	cd backend && pytest tests/integration/ -v

test-e2e:
	cd frontend && npx playwright test

# ── Lint ──────────────────────────────────────────────────────────────────────
lint:
	@echo "🔍 Linting backend..."
	cd backend && ruff check .
	@echo "🔍 Linting frontend..."
	cd frontend && npm run lint

format:
	cd backend && ruff format .
	cd backend && ruff check --fix .

# ── Help ──────────────────────────────────────────────────────────────────────
help:
	@echo "InsightFlow v2 — Available commands:"
	@echo "  make install        Install all dependencies"
	@echo "  make dev            Start backend + frontend in dev mode"
	@echo "  make docker-up      Start PostgreSQL + Redis via Docker"
	@echo "  make migrate        Run database migrations"
	@echo "  make test           Run full test suite"
	@echo "  make lint           Run linters"
