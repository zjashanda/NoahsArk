.PHONY: install migrate seed api test lint typecheck secret-scan ui-check
install:
	python -m pip install -e '.[dev]'
migrate:
	alembic upgrade head
seed:
	python -m noahsark.seed
api:
	uvicorn noahsark.main:app --host 127.0.0.1 --port 8000
test:
	pytest --disable-warnings -q
lint:
	ruff check noahsark tests
typecheck:
	mypy noahsark
secret-scan:
	../../scripts/secret-scan.sh
ui-check:
	cd ../../design/ui-app && node checks/contract-check.mjs && node checks/smoke-check.mjs
