.PHONY: check fmt

# Run every quality gate that CI runs.
check:
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest

# Apply formatting and safe lint fixes.
fmt:
	cd backend && uv run ruff format . && uv run ruff check --fix .
