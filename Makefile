.PHONY: install dev api dashboard test lint migrate seed clean docker-up docker-down

# ── Setup ──────────────────────────────────────────────────────────────────────
install:
	pip install -r requirements.txt

# ── Development ────────────────────────────────────────────────────────────────
dev: migrate seed
	@echo "✅  Dev environment ready."

api:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

dashboard:
	streamlit run app/dashboard/streamlit_app.py --server.port 8501

# ── Database ───────────────────────────────────────────────────────────────────
migrate:
	alembic upgrade head

migrate-create:
	alembic revision --autogenerate -m "$(msg)"

seed:
	python scripts/generate_data.py
	python scripts/seed_db.py

# ── ML Pipeline ────────────────────────────────────────────────────────────────
train:
	python ml/pipeline/run_pipeline.py

# ── Testing ────────────────────────────────────────────────────────────────────
test:
	pytest tests/ -v --tb=short

test-api:
	pytest tests/api/ -v --tb=short

test-unit:
	pytest tests/unit/ -v --tb=short

# ── Lint ───────────────────────────────────────────────────────────────────────
lint:
	ruff check app/ ml/ scripts/
	ruff format --check app/ ml/ scripts/

# ── Docker ─────────────────────────────────────────────────────────────────────
docker-up:
	docker compose up --build -d

docker-down:
	docker compose down -v

docker-logs:
	docker compose logs -f api

# ── Clean ──────────────────────────────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	rm -f kumip.db
