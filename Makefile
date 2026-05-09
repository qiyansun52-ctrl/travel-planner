.PHONY: gen-types check-types launch-check smoke regression

gen-types:
	cd web && npm run gen:types

check-types:
	cd web && npm run check:types

launch-check:
	python3 scripts/check_launch_readiness.py

smoke:
	cd api && bash scripts/run_fixture_smoke.sh

regression:
	python3 scripts/check_launch_readiness.py
	cd web && npm run check:types
	git diff --exit-code api/dist/schema.json web/src/lib/generated/types.ts
	cd web && npm run lint
	cd web && npm run test
	cd web && npm run build
	cd api && uv run pytest -v
	cd api && uv run ruff check app tests scripts
	cd api && bash scripts/run_fixture_smoke.sh
	cd web && npm run test:e2e
