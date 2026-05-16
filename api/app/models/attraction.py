"""Attraction card models — mirror of TypeScript AttractionCard, DiscoverSections."""

from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

CardSection = Literal["experience", "transport", "food"]


class AttractionCard(BaseModel):
    """Single discoverable item shown in the gallery."""

    id: str
    name: str
    section: CardSection
    description: str
    estimated_cost: str
    image_url: str
    tags: list[str]

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class DiscoverSections(BaseModel):
    """Three-section response shape returned by /api/discover."""

    experience: list[AttractionCard]
    transport: list[AttractionCard]
    food: list[AttractionCard]
