"""User preferences model — mirror of TypeScript UserPreferences."""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class UserPreferences(BaseModel):
    """Trip preferences gathered from the home form + selection bar."""

    destination: str
    departure_city: str
    departure_date: str
    days: int
    total_budget: int
    accommodation_description: str
    experience_description: str

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
