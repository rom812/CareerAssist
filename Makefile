.PHONY: help setup setup-backend setup-frontend setup-hooks \
       lint lint-backend lint-frontend format format-check \
       test test-full package deploy ci clean

# Self-documenting help
help: ## Show this help message
	@echo "CareerAssist Development Commands"
	@echo "================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ---------- Setup ----------

setup: setup-backend setup-frontend setup-hooks ## Install all dependencies

setup-backend: ## Install backend Python dependencies
	cd backend && uv sync --group dev

setup-frontend: ## Install frontend Node dependencies
	cd frontend && npm ci

setup-hooks: ## Install pre-commit hooks
	pre-commit install

# ---------- Linting ----------

lint: lint-backend lint-frontend ## Run all linters

lint-backend: ## Run Ruff linter on backend
	cd backend && uv run ruff check .

lint-frontend: ## Run ESLint on frontend
	cd frontend && npm run lint

# ---------- Formatting ----------

format: ## Auto-format backend code
	cd backend && uv run ruff format .
	cd backend && uv run ruff check --fix .

format-check: ## Check formatting without changes
	cd backend && uv run ruff format --check .

# ---------- Testing ----------

test: ## Run mocked unit tests
	cd backend && MOCK_LAMBDAS=true uv run test_simple.py

test-full: ## Run integration tests (requires AWS)
	cd backend && uv run test_full.py

# ---------- Packaging & Deploy ----------

package: ## Package all Lambda functions
	cd backend && uv run deploy_all_lambdas.py --package

deploy: ## Deploy Lambda functions via Terraform
	cd backend && uv run deploy_all_lambdas.py

# ---------- CI ----------

ci: lint format-check test ## Run full CI pipeline locally

# ---------- Cleanup ----------

clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name build_temp -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
