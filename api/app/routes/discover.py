"""POST /api/discover endpoint.

Mirrors the behavior of `web/src/app/api/discover/route.ts`:
1. Run three Tavily searches in parallel.
2. Pass all results to Gemini with the discover prompt.
3. Return JSON shaped { sections: { experience, transport, food } }.
"""

from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.models.attraction import AttractionCard, DiscoverSections
from app.prompts.discover import build_discover_prompt
from app.services.gemini import extract_json_block, generate_text
from app.services.tavily import search_tavily_three_sections

router = APIRouter()


@router.get("/api/discover", response_model=dict)
async def discover(destination: str) -> dict:
    """Generate three-section attraction cards for a destination."""
    if not destination:
        raise HTTPException(status_code=400, detail="destination is required")

    settings = get_settings()

    experience_items, transport_items, food_items = await search_tavily_three_sections(
        destination, settings.tavily_api_key
    )

    prompt = build_discover_prompt(destination, experience_items, transport_items, food_items)

    try:
        raw = await generate_text(prompt)
        parsed = extract_json_block(raw)
    except Exception as err:
        raise HTTPException(status_code=502, detail=f"LLM failed: {err}") from err

    def to_cards(raw_cards: list[dict], section: str) -> list[AttractionCard]:
        return [
            AttractionCard(
                id=str(uuid4()),
                name=c.get("name", ""),
                section=section,  # type: ignore[arg-type]
                description=c.get("description", ""),
                estimatedCost=c.get("estimatedCost", ""),
                imageUrl="",
                tags=c.get("tags", []),
            )
            for c in raw_cards
        ]

    sections = DiscoverSections(
        experience=to_cards(parsed.get("experience", []), "experience"),
        transport=to_cards(parsed.get("transport", []), "transport"),
        food=to_cards(parsed.get("food", []), "food"),
    )
    return {"sections": sections.model_dump(by_alias=True)}
