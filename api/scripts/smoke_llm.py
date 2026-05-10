"""Smoke test: real Gemini call returning a structured object.

Usage:
    cd api && uv run python scripts/smoke_llm.py

Requires GEMINI_API_KEY (or LLM_PROVIDER_API_KEY) in env.
This is NOT run in pytest -- it hits the real API and costs money/quota.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class CityHint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    city: str = Field(description="The city the user is asking about")
    country_code: str = Field(description="ISO-3166 alpha-2 code, uppercase")


async def main() -> int:
    from app.config import load_environment

    load_environment()
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("LLM_PROVIDER_API_KEY")):
        print("[smoke] failed: no GEMINI_API_KEY in env", file=sys.stderr)
        return 1

    from app.llm import generate_structured

    result = await generate_structured(
        system="You return strict JSON matching the requested schema.",
        user='Return JSON for: {"city":"Shanghai"}. Include the ISO country code.',
        schema=CityHint,
        label="smoke.city_hint",
    )
    print(f"[smoke] OK city={result.city} country={result.country_code}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
