.PHONY: requirements run clean test lint format type-check pre-commit install-dev help

VENV := venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# Create virtual environment if it doesn't exist
$(VENV):
	@echo "Creating virtual environment..."
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	@echo "Installing dependencies from requirements.txt..."
	$(PIP) install -r requirements.txt
	@echo "✅ Virtual environment ready at $(VENV)/"

# Update requirements.txt from requirements.in (requires pip-tools)
update-requirements: $(VENV)  ## Update requirements.txt from requirements.in
	$(PIP) install pip-tools
	$(VENV)/bin/pip-compile --upgrade requirements.in -o requirements.txt
	@echo "✅ requirements.txt updated. Run 'make requirements' to install."

# Install/sync dependencies from requirements.txt
requirements: $(VENV)  ## Install/sync dependencies from requirements.txt
	@echo "Syncing dependencies from requirements.txt..."
	$(PIP) install -r requirements.txt
	@echo "✅ Dependencies installed in $(VENV)/"

install-dev: $(VENV)  ## Install development dependencies and setup pre-commit
	@echo "Installing pre-commit hooks..."
	$(VENV)/bin/pre-commit install
	@echo "✅ Pre-commit hooks installed"

# Start the streamlit portal
run: $(VENV)  ## Run the Streamlit application
	@echo "Starting Streamlit portal..."
	$(PYTHON) -m streamlit run portal.py

test: $(VENV)  ## Run all tests with coverage
	@echo "Running tests with coverage..."
	$(VENV)/bin/pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html

test-quick: $(VENV)  ## Run tests without coverage (faster)
	@echo "Running quick tests..."
	$(VENV)/bin/pytest tests/ -v

lint: $(VENV)  ## Run ruff linter
	@echo "Running linter..."
	$(VENV)/bin/ruff check .

lint-fix: $(VENV)  ## Run ruff linter with auto-fix
	@echo "Running linter with auto-fix..."
	$(VENV)/bin/ruff check . --fix

format: $(VENV)  ## Format code with ruff
	@echo "Formatting code..."
	$(VENV)/bin/ruff format .

format-check: $(VENV)  ## Check code formatting without changes
	@echo "Checking code formatting..."
	$(VENV)/bin/ruff format --check .

type-check: $(VENV)  ## Run mypy type checker
	@echo "Running type checker..."
	$(VENV)/bin/mypy . --ignore-missing-imports --check-untyped-defs

pre-commit: $(VENV)  ## Run all pre-commit hooks
	@echo "Running pre-commit hooks..."
	$(VENV)/bin/pre-commit run --all-files

clean:  ## Clean up generated files
	@echo "Cleaning up generated files..."
	rm -rf $(VENV) __pycache__ .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	@echo "✅ Cleanup complete"

verify: $(VENV)  ## Run all quality checks (lint, type-check, test)
	@echo "🔍 Running all quality checks..."
	@echo ""
	@echo "1️⃣  Linting..."
	@$(VENV)/bin/ruff check .
	@echo "✅ Linting passed!"
	@echo ""
	@echo "2️⃣  Type checking..."
	@$(VENV)/bin/mypy . --ignore-missing-imports --check-untyped-defs
	@echo "✅ Type checking passed!"
	@echo ""
	@echo "3️⃣  Testing..."
	@$(VENV)/bin/pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html
	@echo ""
	@echo "✅ All checks passed! Virtual environment: $(VENV)/"
