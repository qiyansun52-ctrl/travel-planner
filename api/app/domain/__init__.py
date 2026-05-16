"""Pure domain logic with no I/O, LLM, or provider calls."""

from app.domain.budget import (
    DEFAULT_ATTRACTION_SHARE,
    calculate_daily_attraction_slot,
    classify_attraction_cost_signal,
    sum_budget_bands,
    to_per_trip_band,
)
from app.domain.geography import is_china_destination
from app.domain.selection import (
    has_density_warning,
    is_continue_disabled,
    normalize_selected_card_ids,
)
from app.domain.validator import (
    OperatingWindow,
    ValidatorContext,
    validate_itinerary,
)

__all__ = [
    "DEFAULT_ATTRACTION_SHARE",
    "OperatingWindow",
    "ValidatorContext",
    "calculate_daily_attraction_slot",
    "classify_attraction_cost_signal",
    "has_density_warning",
    "is_china_destination",
    "is_continue_disabled",
    "normalize_selected_card_ids",
    "sum_budget_bands",
    "to_per_trip_band",
    "validate_itinerary",
]
