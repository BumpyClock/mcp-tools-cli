# ABOUTME: Makefile for common development tasks and test execution
# ABOUTME: Provides convenient shortcuts for testing, formatting, and development workflow

.PHONY: help test test-unit test-integration test-performance test-compatibility test-smoke test-all test-coverage test-fast
.PHONY: format lint check install install-dev clean coverage-html serve-coverage
.PHONY: setup-dev setup-test setup-hooks pre-commit

# Default Python interpreter
PYTHON := python
PIP := $(PYTHON) -m pip
PYTEST := $(PYTHON) -m pytest

# Project directories
SRC_DIR := src
TEST_DIR := tests
SCRIPTS_DIR := scripts

# Help target
help: ## Show this help message
	@echo "MCP Manager Development Commands"
	@echo "================================"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation targets
install: ## Install package in development mode
	$(PIP) install -e .

install-dev: ## Install package with development dependencies
	$(PIP) install -e .[dev,testing,integration]

install-test: ## Install package with testing dependencies only
	$(PIP) install -e .[testing]

# Test targets
test: ## Run fast tests (unit tests, no slow tests)
	$(PYTHON) $(SCRIPTS_DIR)/run_tests.py fast

test-unit: ## Run unit tests only
	$(PYTHON) $(SCRIPTS_DIR)/run_tests.py unit

test-integration: ## Run integration tests
	$(PYTHON) $(SCRIPTS_DIR)/run_tests.py integration

test-performance: ## Run performance tests
	$(PYTHON) $(SCRIPTS_DIR)/run_tests.py performance

test-compatibility: ## Run compatibility tests
	$(PYTHON) $(SCRIPTS_DIR)/run_tests.py compatibility

test-smoke: ## Run smoke tests for quick validation
	$(PYTHON) $(SCRIPTS_DIR)/run_tests.py smoke

test-all: ## Run all tests
	$(PYTHON) $(SCRIPTS_DIR)/run_tests.py all

test-comprehensive: ## Run comprehensive test suite
	$(PYTHON) $(SCRIPTS_DIR)/run_tests.py comprehensive

test-coverage: ## Run tests with coverage reporting
	$(PYTHON) $(SCRIPTS_DIR)/run_tests.py coverage

test-parallel: ## Run tests in parallel
	$(PYTEST) $(TEST_DIR) -n auto --tb=short -v

test-fast: ## Run only fast tests (exclude slow and performance tests)
	$(PYTEST) $(TEST_DIR) -m "not slow and not performance" --tb=line -x

# Code quality targets
format: ## Format code with black and isort
	black $(SRC_DIR) $(TEST_DIR)
	isort $(SRC_DIR) $(TEST_DIR)

lint: ## Run linting tools
	black --check $(SRC_DIR) $(TEST_DIR)
	isort --check-only $(SRC_DIR) $(TEST_DIR)
	mypy $(SRC_DIR)/mcp_manager/ --ignore-missing-imports
	flake8 $(SRC_DIR) $(TEST_DIR) --max-line-length=88 --extend-ignore=E203,W503

check: lint ## Alias for lint

# Coverage targets
coverage-html: ## Generate HTML coverage report
	$(PYTEST) $(TEST_DIR) --cov=$(SRC_DIR)/mcp_manager --cov-report=html:htmlcov --cov-report=term-missing

serve-coverage: coverage-html ## Generate and serve HTML coverage report
	@echo "Opening coverage report in browser..."
	@if command -v xdg-open > /dev/null; then \
		xdg-open htmlcov/index.html; \
	elif command -v open > /dev/null; then \
		open htmlcov/index.html; \
	elif command -v start > /dev/null; then \
		start htmlcov/index.html; \
	else \
		echo "Coverage report generated in htmlcov/index.html"; \
	fi

# Development setup targets
setup-dev: install-dev setup-hooks ## Set up complete development environment
	@echo "Development environment setup complete!"

setup-test: install-test ## Set up testing environment only
	@echo "Testing environment setup complete!"

setup-hooks: ## Set up pre-commit hooks
	@if command -v pre-commit > /dev/null; then \
		pre-commit install; \
		echo "Pre-commit hooks installed!"; \
	else \
		echo "pre-commit not found. Install with: pip install pre-commit"; \
	fi

pre-commit: ## Run pre-commit hooks on all files
	pre-commit run --all-files

# Utility targets
clean: ## Clean up build artifacts and temporary files
	@echo "Cleaning up..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage*
	rm -rf coverage.xml
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
	@echo "Clean up complete!"

# Quick commands for different workflows
dev: format test-fast ## Quick development workflow (format + fast tests)

ci: lint test-all ## CI workflow (lint + all tests)

release-check: lint test-comprehensive ## Pre-release check (lint + comprehensive tests)

# Platform-specific test runners
test-windows: ## Run tests optimized for Windows
	powershell -ExecutionPolicy Bypass -File $(SCRIPTS_DIR)/test_quick.ps1 -TestType fast

test-unix: ## Run tests optimized for Unix-like systems
	bash $(SCRIPTS_DIR)/test_quick.sh --type fast

# Performance monitoring
test-memory: ## Run tests with memory monitoring
	$(PYTEST) $(TEST_DIR) --tb=short -v --memmon

test-benchmark: ## Run performance benchmarks
	$(PYTEST) $(TEST_DIR)/performance/ --benchmark-only --tb=short

# Debug targets
test-debug: ## Run tests with debugging enabled
	$(PYTEST) $(TEST_DIR) --tb=long -vv --capture=no

test-pdb: ## Run tests with PDB on failure
	$(PYTEST) $(TEST_DIR) --pdb --tb=short -x

# Documentation targets
docs-test: ## Test that documentation examples work
	$(PYTEST) docs/ --doctest-modules

# Default target
.DEFAULT_GOAL := help