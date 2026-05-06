"""Async wrapper around the new google-genai SDK."""

import json
import re
from functools import lru_cache

from google import genai

from app.config import get_settings


@lru_cache(maxsize=1)
def _client() -> genai.Client:
    """Cached Gemini client. The Client itself is thread-safe."""
    return genai.Client(api_key=get_settings().gemini_api_key)


async def generate_text(prompt: str) -> str:
    """Run Gemini once with the given prompt, return raw text response."""
    response = await _client().aio.models.generate_content(
        model=get_settings().gemini_model,
        contents=prompt,
    )
    return response.text or ""


def extract_json_block(raw: str) -> dict:
    """Extract the first JSON object from an LLM response.

    Robust against markdown code fences, trailing commas, and trailing prose.
    Raises ValueError if no JSON is recoverable.
    """
    cleaned = re.sub(r"```(?:json)?\n?", "", raw).strip()

    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        raise ValueError("No JSON object found in response")
    candidate = match.group(0)

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    candidate2 = re.sub(r",(\s*[}\]])", r"\1", candidate)
    try:
        return json.loads(candidate2)
    except json.JSONDecodeError:
        pass

    last_brace = candidate2.rfind("}")
    if last_brace > 0:
        try:
            return json.loads(candidate2[: last_brace + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError("JSON parse failed after sanitization attempts")
