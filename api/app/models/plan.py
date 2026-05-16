"""Travel plan models — mirror of TypeScript TravelPlan and friends."""

from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.models.attraction import AttractionCard
from app.models.preferences import UserPreferences

ActivityType = Literal["attraction", "food", "transport", "hotel", "free"]


class Activity(BaseModel):
    id: str
    time: str
    end_time: str | None = None
    place: str
    description: str
    type: ActivityType
    estimated_cost: int | None = None
    tips: str | None = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class DayPlan(BaseModel):
    day: int
    date: str
    title: str
    activities: list[Activity]
    total_cost: int

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class BudgetBreakdown(BaseModel):
    transport: int
    accommodation: int
    food: int
    attractions: int
    other: int
    total: int


class TravelPlan(BaseModel):
    id: str
    preferences: UserPreferences
    selected_attractions: list[AttractionCard]
    days: list[DayPlan]
    budget: BudgetBreakdown
    tips: list[str]
    created_at: str

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
