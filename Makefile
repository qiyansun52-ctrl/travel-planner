.PHONY: gen-types check-types launch-check production-check ops-summary smoke smoke-real regression

gen-types:
	cd web && npm run gen:types

check-types:
	cd web && npm run check:types

launch-check:
	python3 scripts/check_launch_readiness.py

production-check:
	cd api && uv run python scripts/check_production_readiness.py

ops-summary:
	cd api && uv run python scripts/ops_summary.py

smoke:
	cd api && bash scripts/run_fixture_smoke.sh

smoke-real:
	cd api && uv run python scripts/smoke_llm.py
	cd api && uv run python scripts/smoke_amap_mcp.py

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
