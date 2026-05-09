from app.domain.geography import is_china_destination


def test_is_china_destination_returns_true_for_cn() -> None:
    assert is_china_destination("CN") is True


def test_is_china_destination_returns_false_for_other() -> None:
    assert is_china_destination("US") is False
    assert is_china_destination("JP") is False
    assert is_china_destination("cn") is False
    assert is_china_destination("") is False
