from __future__ import annotations

import json
import sys
from importlib import import_module
from pathlib import Path
from typing import TypeAlias

from pydantic import BaseModel

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

SchemaModel: TypeAlias = type[BaseModel]
DEFAULT_OUTPUT = API_ROOT / "dist" / "schema.json"

ROOT_MODEL_NAMES: tuple[str, ...] = (
    "Coordinate",
    "NormalizedPlace",
    "BudgetBand",
    "NormalizedRoute",
    "DiscoveryCard",
    "AreaSummary",
    "FoodSummary",
    "SourceNote",
    "BudgetSummary",
    "DiscoveryOutput",
    "SampleHotel",
    "StayOption",
    "StayRecommendation",
    "TransportLeg",
    "IntracityStrategy",
    "TransportRecommendation",
    "ValidatorIssue",
    "ItinerarySegment",
    "ItineraryDay",
    "Itinerary",
    "HardConstraints",
    "Preference",
    "AdjustmentRequest",
    "ConversationTurn",
    "DiscoveryState",
    "PlanningSession",
)


def root_models() -> tuple[SchemaModel, ...]:
    schemas = import_module("app.models.schemas")
    return tuple(getattr(schemas, name) for name in ROOT_MODEL_NAMES)


def build_schema_document() -> dict[str, object]:
    defs: dict[str, object] = {}
    for model in root_models():
        schema = model.model_json_schema(ref_template="#/$defs/{model}")
        nested_defs = schema.pop("$defs", {})
        defs.update(nested_defs)
        defs[model.__name__] = schema

    ordered_defs = {name: defs[name] for name in sorted(defs)}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "TravelPlannerSchemas",
        "type": "object",
        "$defs": ordered_defs,
    }


def export_schema(output_path: Path = DEFAULT_OUTPUT) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(build_schema_document(), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    export_schema()
