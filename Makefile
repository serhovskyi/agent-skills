.PHONY: test lint

# The harness suite, also what .github/workflows/test.yml runs. ARGS narrows it:
#   make test ARGS="harness/tests/test_hook_rules.py -k git"
test:
	uv run --with pytest python -m pytest harness/tests -q -p no:cacheprovider $(ARGS)

lint:
	uvx ruff check harness skills/wave-prep/scripts
	uvx ruff format --check harness
