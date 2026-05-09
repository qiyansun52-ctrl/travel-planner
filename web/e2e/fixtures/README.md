# E2E fixture mode

Playwright does not mock browser responses in these specs. The Playwright
webServer starts the app with `E2E_FIXTURE_MODE=1`, which runs the FastAPI
backend against deterministic fixture data.

Shared fixture helpers live in `api/app/*/fixtures.py`; discovery cards are
assembled by the fixture branch in `api/app/graph/nodes/discovery.py`.
