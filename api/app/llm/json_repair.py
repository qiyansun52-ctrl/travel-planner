"""LLM output JSON repair -- port of web/src/server/llm/jsonRepair.ts.

Strips non-JSON prefix/suffix, fixes trailing commas, balances delimiters.
"""
from __future__ import annotations

import json
import re
from typing import Any

_TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")


class JsonRepairError(ValueError):
    """Raised when the repair pipeline cannot recover a JSON payload."""


def repair_json(raw: str) -> str:
    candidate = extract_json_candidate(raw)
    return _TRAILING_COMMA_RE.sub(r"\1", candidate)


def parse_json_with_repair(raw: str) -> Any:
    return json.loads(repair_json(raw))


def extract_json_candidate(raw: str) -> str:
    start = _find_first_json_start(raw)
    if start == -1:
        raise JsonRepairError("No JSON payload found in LLM output")

    end = _find_balanced_json_end(raw, start)
    if end == -1:
        raise JsonRepairError("No complete JSON payload found in LLM output")

    return raw[start : end + 1].strip()


def _find_first_json_start(raw: str) -> int:
    obj_start = raw.find("{")
    arr_start = raw.find("[")
    if obj_start == -1:
        return arr_start
    if arr_start == -1:
        return obj_start
    return min(obj_start, arr_start)


def _find_balanced_json_end(raw: str, start: int) -> int:
    stack: list[str] = []
    in_string = False
    escaped = False

    for i in range(start, len(raw)):
        ch = raw[i]

        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            stack.append("}")
            continue
        if ch == "[":
            stack.append("]")
            continue
        if ch in ("}", "]"):
            if not stack:
                raise JsonRepairError("Mismatched JSON delimiters in LLM output")
            expected = stack.pop()
            if expected != ch:
                raise JsonRepairError("Mismatched JSON delimiters in LLM output")
            if not stack:
                return i

    return -1
