.PHONY: test lint format

# The harness suite, also what .github/workflows/test.yml runs. ARGS narrows it:
#   make test ARGS="harness/tests/test_hook_rules.py -k git"
test:
	uv run --with pytest python -m pytest harness/tests -q -p no:cacheprovider $(ARGS)

# ruff.toml lists what is linted: the hooks, the tools, the tests and the wave-prep scripts.
lint:
	uvx ruff check .
	uvx ruff format --check .

format:
	uvx ruff check . --fix
	uvx ruff format .
