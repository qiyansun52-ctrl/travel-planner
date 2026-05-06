"""POST /api/plan/generate endpoint.

Handles two modes:
1. New plan generation — body has `preferences` and optional `selectedAttractions`.
2. Adjustment — body has `currentPlan` (JSON string), `adjustment` (text), and
   optional `selectedAttractions` for context.

Returns plain text (raw LLM JSON output) for compatibility with the frontend's
existing parse logic.
"""

from typing import Annotated

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import PlainTextResponse

from app.models.attraction import AttractionCard
from app.models.preferences import UserPreferences
from app.prompts.plan import build_adjustment_prompt, build_plan_prompt
from app.services.gemini import generate_text

router = APIRouter()


@router.post("/api/plan/generate", response_class=PlainTextResponse)
async def generate_plan(
    body: Annotated[dict, Body(...)],
) -> str:
    """Either generate a new plan or apply an adjustment."""
    selected_raw = body.get("selectedAttractions") or []
    selected = [AttractionCard.model_validate(c) for c in selected_raw]

    if body.get("currentPlan") and body.get("adjustment"):
        prompt = build_adjustment_prompt(
            body["currentPlan"], body["adjustment"], selected
        )
    elif body.get("preferences"):
        prefs = UserPreferences.model_validate(body["preferences"])
        prompt = build_plan_prompt(prefs, selected)
    else:
        raise HTTPException(
            status_code=400,
            detail="must provide either preferences or (currentPlan + adjustment)",
        )

    try:
        return await generate_text(prompt)
    except Exception as err:
        raise HTTPException(status_code=502, detail=f"LLM failed: {err}") from err
