"""Discovery selection helpers ported from web/src/domain/selection.ts."""
from __future__ import annotations


def normalize_selected_card_ids(selected: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for card_id in selected:
        if not card_id or card_id in seen:
            continue
        seen.add(card_id)
        result.append(card_id)
    return result


def is_continue_disabled(selected: list[str]) -> bool:
    return len(normalize_selected_card_ids(selected)) == 0


def has_density_warning(selected_count: int, duration_days: int) -> bool:
    return selected_count > duration_days * 5
