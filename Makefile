.PHONY: gen-types check-types regression

gen-types:
	cd web && npm run gen:types

check-types:
	cd web && npm run check:types

regression:
	cd web && npm run check:types
	cd web && npm run lint
	cd web && npm run test
	cd web && npm run build
	cd api && uv run pytest -v
	cd api && uv run ruff check app tests scripts
	cd web && npm run test:e2e
