"""Deterministic adjustment request classifier."""

from __future__ import annotations

import re

from app.models.schemas import AdjustmentRequest


def classify_adjustment(raw_text: str) -> AdjustmentRequest:
    text = raw_text.strip()
    lower = text.lower()

    if not text or len(text) < 4:
        return _base(text, "unknown", 0.2, "none", None)

    if re.search(
        r"预算|天数|人数|目的地|出发日期|departure|budget|destination|traveler|duration",
        text,
        re.IGNORECASE,
    ):
        return _base(text, "C", 0.86, _root_scope(lower), text)

    if re.search(r"酒店|住宿|住|hotel|stay|area|区域|民宿|homestay", text, re.IGNORECASE):
        return _base(text, "B", 0.82, "stay", text)

    if re.search(
        r"交通|高铁|火车|飞机|航班|rail|train|flight|transport",
        text,
        re.IGNORECASE,
    ):
        return _base(text, "B", 0.82, "transport", text)

    if re.search(r"轻松|紧凑|换|删除|添加|第二天|下午|itinerary|plan|day", text, re.IGNORECASE):
        return _base(text, "A", 0.78, "day", text)

    return _base(text, "unknown", 0.45, "none", None)


def _base(
    raw_text: str,
    type_: str,
    confidence: float,
    target_scope: str,
    proposed_change: str | None,
) -> AdjustmentRequest:
    return AdjustmentRequest(
        raw_text=raw_text,
        type=type_,
        confidence=confidence,
        target_scope=target_scope,
        proposed_change=proposed_change,
    )


def _root_scope(text: str) -> str:
    if re.search(r"budget|预算", text, re.IGNORECASE):
        return "budget"
    if re.search(r"duration|天数", text, re.IGNORECASE):
        return "duration"
    if re.search(r"destination|目的地", text, re.IGNORECASE):
        return "destination"
    if re.search(r"traveler|人数", text, re.IGNORECASE):
        return "traveler_count"
    return "none"
