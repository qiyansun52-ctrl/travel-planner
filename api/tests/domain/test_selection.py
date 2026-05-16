from app.domain.selection import (
    has_density_warning,
    is_continue_disabled,
    normalize_selected_card_ids,
)


def test_normalize_dedupes_and_drops_falsy() -> None:
    assert normalize_selected_card_ids(["a", "b", "a", "", "c"]) == ["a", "b", "c"]


def test_is_continue_disabled_when_no_real_selection() -> None:
    assert is_continue_disabled([]) is True
    assert is_continue_disabled(["", ""]) is True


def test_is_continue_disabled_false_when_at_least_one_real_id() -> None:
    assert is_continue_disabled(["x"]) is False


def test_has_density_warning_above_5_per_day() -> None:
    assert has_density_warning(11, 2) is True
    assert has_density_warning(10, 2) is False
    assert has_density_warning(0, 2) is False
