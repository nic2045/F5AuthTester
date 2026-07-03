# F5AuthTester — developer tasks.
# Usage: `make <target>`. Override vars, e.g. `make dev PORT=9000 CONFIG=./my.yaml`.

PYTHON ?= python3
HOST   ?= 127.0.0.1
PORT   ?= 8080
CONFIG ?= config.yaml

# Export CONFIG only if the file exists, so `make demo` / a missing file falls back to the
# built-in demo config instead of erroring.
ifneq ("$(wildcard $(CONFIG))","")
export F5AUTHTESTER_CONFIG = $(CONFIG)
endif

.DEFAULT_GOAL := help

.PHONY: help install dev serve run demo check test lint fmt clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

install: ## Install the app + dev tools (editable)
	$(PYTHON) -m pip install -e ".[dev]"

dev: ## Run the dashboard with auto-reload (uses $(CONFIG) if present)
	$(PYTHON) -m f5authtester serve --host $(HOST) --port $(PORT) --reload

serve run: ## Run the dashboard (no reload)
	$(PYTHON) -m f5authtester serve --host $(HOST) --port $(PORT)

demo: ## Run the dashboard with the built-in demo config (ignores $(CONFIG))
	F5AUTHTESTER_CONFIG= $(PYTHON) -m f5authtester serve --host $(HOST) --port $(PORT)

check: ## Run all checks once against $(CONFIG) and print a report (env/config smoke test)
	$(PYTHON) -m f5authtester check

test: ## Run the pytest suite
	$(PYTHON) -m pytest

lint: ## Ruff lint + format check
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

fmt: ## Auto-format and auto-fix with ruff
	$(PYTHON) -m ruff format .
	$(PYTHON) -m ruff check --fix .

clean: ## Remove caches and build artifacts
	rm -rf .pytest_cache .ruff_cache build dist *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
