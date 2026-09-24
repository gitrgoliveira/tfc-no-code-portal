.PHONY: help requirements update-requirements upgrade-package install-dev run test test-quick lint lint-fix \
	format format-check type-check audit audit-lock bandit pre-commit clean verify

VENV := venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
# Stamp recording the last install; it is older than requirements.txt whenever the pins change
# (e.g. after a pull), so the targets below that use the venv reinstall before running.
INSTALLED := $(VENV)/.requirements-installed

# requirements.txt is a universal lock: resolved for every platform and for Python $(PYTHON_MIN)+,
# so it comes out the same whichever OS or Python version runs the compile.
# Keep PYTHON_MIN in sync with requires-python in pyproject.toml (tests/test_tooling.py checks the lock).
PYTHON_MIN := 3.11
UV_COMPILE := $(VENV)/bin/uv pip compile --universal --python-version $(PYTHON_MIN) --no-emit-package pip \
	requirements.in -o requirements.txt

# pip-audit settings shared by `make audit` and CI. requirements.txt pins every dependency, so it is
# audited as-is (--no-deps --disable-pip) instead of being re-resolved in a throwaway venv.
PIP_AUDIT ?= $(VENV)/bin/pip-audit
# To accept an advisory that has no fixed release yet, add a line like the one below with the
# reason and a link, and remove it as soon as a fix ships:
#   PIP_AUDIT_IGNORE += --ignore-vuln GHSA-xxxx-xxxx-xxxx  # <package>: no fix yet, <advisory link>
PIP_AUDIT_IGNORE :=

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Create virtual environment if it doesn't exist
$(PYTHON):
	@echo "Creating virtual environment..."
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip

# Install dependencies on first use and again whenever requirements.txt changes
$(INSTALLED): requirements.txt | $(PYTHON)
	@echo "Installing dependencies from requirements.txt..."
	$(PIP) install -r requirements.txt
	@touch $@
	@echo "✅ Virtual environment ready at $(VENV)/"

# Force a reinstall from requirements.txt
requirements: | $(PYTHON)  ## Install/sync dependencies from requirements.txt
	@echo "Syncing dependencies from requirements.txt..."
	$(PIP) install -r requirements.txt
	@touch $(INSTALLED)
	@echo "✅ Dependencies installed in $(VENV)/"

update-requirements: $(INSTALLED)  ## Upgrade all pins in requirements.txt from requirements.in
	$(UV_COMPILE) --upgrade
	@echo "✅ requirements.txt updated. The next make target reinstalls it."

upgrade-package: $(INSTALLED)  ## Upgrade one pin, keeping the rest (make upgrade-package PKG=name)
	@test -n "$(PKG)" || { echo "Usage: make upgrade-package PKG=<package>"; exit 1; }
	$(UV_COMPILE) --upgrade-package $(PKG)
	@echo "✅ $(PKG) upgraded in requirements.txt. The next make target reinstalls it."

install-dev: $(INSTALLED)  ## Install development dependencies and setup pre-commit
	@echo "Installing pre-commit hooks..."
	$(VENV)/bin/pre-commit install
	@echo "✅ Pre-commit hooks installed"

# Start the streamlit portal
run: $(INSTALLED)  ## Run the Streamlit application
	@echo "Starting Streamlit portal..."
	$(PYTHON) -m streamlit run portal.py

test: $(INSTALLED)  ## Run all tests with coverage
	@echo "Running tests with coverage..."
	$(VENV)/bin/pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html

test-quick: $(INSTALLED)  ## Run tests without coverage (faster)
	@echo "Running quick tests..."
	$(VENV)/bin/pytest tests/ -v

lint: $(INSTALLED)  ## Run ruff linter
	@echo "Running linter..."
	$(VENV)/bin/ruff check .

lint-fix: $(INSTALLED)  ## Run ruff linter with auto-fix
	@echo "Running linter with auto-fix..."
	$(VENV)/bin/ruff check . --fix

format: $(INSTALLED)  ## Format code with ruff
	@echo "Formatting code..."
	$(VENV)/bin/ruff format .

format-check: $(INSTALLED)  ## Check code formatting without changes
	@echo "Checking code formatting..."
	$(VENV)/bin/ruff format --check .

type-check: $(INSTALLED)  ## Run mypy type checker
	@echo "Running type checker..."
	$(VENV)/bin/mypy . --ignore-missing-imports --check-untyped-defs

audit: $(INSTALLED)  ## Sync the venv to requirements.txt, then audit it for known vulnerabilities
	@$(MAKE) --no-print-directory audit-lock

audit-lock:  ## Audit requirements.txt only, without a venv (used by CI)
	@echo "Auditing requirements.txt for known vulnerabilities..."
	$(PIP_AUDIT) -r requirements.txt --no-deps --disable-pip $(PIP_AUDIT_IGNORE)

bandit: $(INSTALLED)  ## Scan the code for security issues with bandit (config in pyproject.toml)
	@echo "Running bandit..."
	$(VENV)/bin/bandit -c pyproject.toml -r . -q

pre-commit: $(INSTALLED)  ## Run all pre-commit hooks
	@echo "Running pre-commit hooks..."
	PATH="$(abspath $(VENV))/bin:$$PATH" $(VENV)/bin/pre-commit run --all-files

clean:  ## Clean up generated files
	@echo "Cleaning up generated files..."
	rm -rf $(VENV) __pycache__ .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	@echo "✅ Cleanup complete"

verify: lint format-check type-check test audit bandit  ## Run every check CI runs
	@echo ""
	@echo "✅ All checks passed! Virtual environment: $(VENV)/"
