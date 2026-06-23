.PHONY: install run dev lint clean

# ── Configuration ────────────────────────────────────────────────────────────
PYTHON     := uv run python
PYTEST     := uv run pytest
SRC        := src/trading_bot
TESTS      := tests
SHELL 	   := cmd

# ── Tooling ──────────────────────────────────────────────────────────────────
install:
	uv sync

lint:
	uv run ruff check src/trading_bot

format:
	uv run ruff format src/trading_bot

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# ── Main ─────────────────────────────────────────────────────────────────────
run: ## Run trading bot
	$(PYTHON) -m trading_bot.main

dev:
	$(PYTHON) -m trading_bot.main --debug

run_test:
	$(PYTHON) -m trading_bot.test
