# MAIBA Makefile — entrypoints for the bibliography assistant.
#
# Single source of truth for named tasks. CI and humans both use these.
# Toolchain: uv for Python, make for orchestration. Never pip, never venv.

SHELL := /bin/bash
.SHELLFLAGS := -o pipefail -c

UV     ?= uv
UV_RUN ?= $(UV) run
export PATH := $(HOME)/.local/bin:$(PATH)

.PHONY: help setup sync test lint format check clean

help:
	@echo "MAIBA — My AI Bibliography Assistant"
	@echo ""
	@echo "Targets:"
	@echo "  setup     Install dependencies (uv sync --all-extras)"
	@echo "  sync      Sync dependencies (uv sync)"
	@echo "  test      Run pytest"
	@echo "  lint      Run ruff check"
	@echo "  format    Run ruff format"
	@echo "  check     lint + test"
	@echo "  clean     Remove build artifacts"
	@echo ""
	@echo "Once code lands:"
	@echo "  uv run maiba --help          CLI entrypoint"
	@echo ""
	@echo "Tickets: see .claude/rules/tickets.md"
	@echo "Design:  see ARCHITECTURE.md (§2 has the open questions)"

setup:
	$(UV) sync --all-extras

sync:
	$(UV) sync

test:
	$(UV_RUN) pytest

lint:
	$(UV_RUN) ruff check src tests

format:
	$(UV_RUN) ruff format src tests

check: lint test

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache build dist *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
