"""Geography helpers ported from web/src/domain/geography.ts."""
from __future__ import annotations


def is_china_destination(country_code: str) -> bool:
    return country_code == "CN"
