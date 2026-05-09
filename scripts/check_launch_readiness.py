#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

API_ENV_REQUIRED = {
    "GEMINI_API_KEY",
    "TAVILY_API_KEY",
    "GEMINI_MODEL",
    "AMAP_API_KEY",
    "MAPBOX_ACCESS_TOKEN",
    "SESSION_DATA_DIR",
    "METRICS_DATA_DIR",
    "CORS_ORIGINS",
    "E2E_FIXTURE_MODE",
    "HOST",
    "PORT",
}

WEB_ENV_REQUIRED = {"NEXT_PUBLIC_API_URL"}

WEB_ENV_FORBIDDEN = {
    "GEMINI_API_KEY",
    "TAVILY_API_KEY",
    "LLM_PROVIDER_API_KEY",
    "SEARCH_PROVIDER_API_KEY",
    "AMAP_API_KEY",
    "MAPBOX_ACCESS_TOKEN",
    "WEATHER_PROVIDER_API_KEY",
}

WEB_PACKAGE_FORBIDDEN = {
    "@anthropic-ai/sdk",
    "@google/generative-ai",
    "zod",
    "jest",
    "@types/jest",
    "jest-environment-jsdom",
    "ts-jest",
}


def parse_env_keys(path: Path, failures: list[str]) -> set[str]:
    keys: set[str] = set()
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            failures.append(f"{path}: line {line_number} must be KEY=value")
            continue
        keys.add(stripped.split("=", 1)[0])
    return keys


def require_contains(
    path: Path,
    needle: str,
    failures: list[str],
    *,
    reason: str,
) -> None:
    text = path.read_text()
    if needle not in text:
        failures.append(f"{path}: missing {needle!r} ({reason})")


def require_not_contains(
    path: Path,
    needle: str,
    failures: list[str],
    *,
    reason: str,
) -> None:
    text = path.read_text()
    if needle in text:
        failures.append(f"{path}: remove stale {needle!r} ({reason})")


def require_path_exists(path: Path, failures: list[str], *, reason: str) -> None:
    if not path.exists():
        failures.append(f"{path}: missing ({reason})")


def require_path_not_exists(path: Path, failures: list[str], *, reason: str) -> None:
    if path.exists():
        failures.append(f"{path}: should not exist ({reason})")


def check_env_examples(failures: list[str]) -> None:
    api_keys = parse_env_keys(ROOT / "api/.env.example", failures)
    web_keys = parse_env_keys(ROOT / "web/.env.example", failures)

    missing_api = sorted(API_ENV_REQUIRED - api_keys)
    if missing_api:
        failures.append(f"api/.env.example missing keys: {', '.join(missing_api)}")

    missing_web = sorted(WEB_ENV_REQUIRED - web_keys)
    if missing_web:
        failures.append(f"web/.env.example missing keys: {', '.join(missing_web)}")

    forbidden_web = sorted(WEB_ENV_FORBIDDEN & web_keys)
    if forbidden_web:
        failures.append(
            "web/.env.example contains backend-only secrets: "
            + ", ".join(forbidden_web)
        )


def check_web_package(failures: list[str]) -> None:
    package_json = json.loads((ROOT / "web/package.json").read_text())
    package_names = set(package_json.get("dependencies", {})) | set(
        package_json.get("devDependencies", {})
    )
    forbidden = sorted(WEB_PACKAGE_FORBIDDEN & package_names)
    if forbidden:
        failures.append(
            "web/package.json contains stale backend/test dependencies: "
            + ", ".join(forbidden)
        )


def check_docs(failures: list[str]) -> None:
    root_readme = ROOT / "README.md"
    api_readme = ROOT / "api/README.md"
    web_readme = ROOT / "web/README.md"
    web_dev_doc = ROOT / "web/docs/development-environment.md"
    launch_checklist = ROOT / "docs/mvp-launch-checklist.md"
    roadmap = ROOT / "docs/superpowers/plans/2026-05-09-langgraph-mvp-roadmap.md"
    makefile = ROOT / "Makefile"

    require_contains(root_readme, "api/.env.example", failures, reason="root setup")
    require_contains(root_readme, "web/.env.example", failures, reason="root setup")
    require_contains(root_readme, "make regression", failures, reason="root verification")
    require_contains(root_readme, "make smoke", failures, reason="root API smoke")
    require_contains(
        root_readme,
        "Plan 1-9 are complete; Plan 10-13 are post-roadmap hardening passes",
        failures,
        reason="root planning status",
    )
    require_not_contains(
        root_readme,
        "Plan 10 is the launch-readiness pass after Plan 9",
        failures,
        reason="stale planning status",
    )

    require_contains(api_readme, "There are no Next.js API routes", failures, reason="cutover")
    for key in sorted(API_ENV_REQUIRED):
        require_contains(
            api_readme,
            key,
            failures,
            reason="API env documentation",
        )
    require_not_contains(
        api_readme,
        "remaining Next.js endpoints are compatibility surfaces",
        failures,
        reason="Plan 7 cutover is complete",
    )
    require_contains(
        api_readme,
        "bash scripts/run_fixture_smoke.sh",
        failures,
        reason="API smoke runner",
    )
    require_contains(
        api_readme,
        "post-roadmap hardening plans live beside it as Plan 10+",
        failures,
        reason="API planning status",
    )
    require_not_contains(
        api_readme,
        "2026-05-09-langgraph-single-city-mvp.md",
        failures,
        reason="old implementation plan pointer",
    )

    require_contains(
        web_readme,
        "NEXT_PUBLIC_API_URL=http://127.0.0.1:8000",
        failures,
        reason="web env",
    )
    require_contains(web_readme, "cd ..\nmake regression", failures, reason="root Makefile")
    require_contains(
        web_readme,
        "fixture-backed API smoke",
        failures,
        reason="web regression docs",
    )
    require_contains(
        web_dev_doc,
        "NEXT_PUBLIC_API_URL=http://127.0.0.1:8000",
        failures,
        reason="web development env",
    )
    require_path_not_exists(
        ROOT / "web/jest.config.ts",
        failures,
        reason="Vitest is the canonical web unit test runner",
    )
    require_contains(
        ROOT / "web/src/lib/apiClient.ts",
        'const DEFAULT_API_URL = "http://127.0.0.1:8000"',
        failures,
        reason="web API default origin",
    )
    require_contains(
        ROOT / "web/next.config.ts",
        "http://127.0.0.1:8000",
        failures,
        reason="Next rewrite default origin",
    )
    for key in sorted(WEB_ENV_FORBIDDEN):
        require_not_contains(
            web_dev_doc,
            key,
            failures,
            reason="backend-only env does not belong in web docs",
        )

    require_contains(launch_checklist, "make regression", failures, reason="launch gate")
    require_contains(
        launch_checklist,
        "make smoke",
        failures,
        reason="launch smoke gate",
    )
    require_not_contains(
        launch_checklist,
        "WEATHER_PROVIDER_API_KEY",
        failures,
        reason="weather provider is an explicit MVP unavailable fallback",
    )
    require_contains(
        launch_checklist,
        "E2E_FIXTURE_MODE=1",
        failures,
        reason="offline flow",
    )
    require_contains(
        launch_checklist,
        "NEXT_PUBLIC_API_URL=http://127.0.0.1:8000",
        failures,
        reason="frontend API target",
    )

    require_contains(makefile, "launch-check:", failures, reason="launch gate target")
    require_contains(makefile, "smoke:", failures, reason="API smoke target")
    require_contains(
        makefile,
        "cd api && bash scripts/run_fixture_smoke.sh",
        failures,
        reason="API smoke target",
    )
    require_contains(
        makefile,
        "git diff --exit-code api/dist/schema.json web/src/lib/generated/types.ts",
        failures,
        reason="generated drift gate",
    )
    require_contains(
        roadmap,
        "**STATUS: COMPLETED (2026-05-10)**",
        failures,
        reason="roadmap closure status",
    )
    require_contains(
        roadmap,
        "- [x] Plan 1-9 全部 DoD 通过",
        failures,
        reason="roadmap DoD closure",
    )
    require_contains(
        roadmap,
        "`make regression` 跑通",
        failures,
        reason="current regression command",
    )
    require_not_contains(
        roadmap,
        "`npm run regression` 跑通",
        failures,
        reason="stale regression command",
    )
    require_path_not_exists(
        ROOT / "web/src/server",
        failures,
        reason="Plan 7 cutover removed server code",
    )
    require_path_exists(
        ROOT / "api/app/graph",
        failures,
        reason="LangGraph workflow package",
    )


def main() -> int:
    failures: list[str] = []
    check_env_examples(failures)
    check_web_package(failures)
    check_docs(failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print("Launch readiness checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
