"""Mirror of web/src/server/llm/jsonRepair.test.ts plus extra edge cases."""
from __future__ import annotations

import pytest

from app.llm.json_repair import (
    JsonRepairError,
    extract_json_candidate,
    parse_json_with_repair,
    repair_json,
)


def test_strips_leading_and_trailing_non_json_text() -> None:
    assert repair_json('Here is the payload:\n{"ok":true}\nDone.') == '{"ok":true}'


def test_fixes_trailing_commas_in_object_and_array() -> None:
    parsed = parse_json_with_repair("""{
      "items": [
        { "name": "Bund", },
      ],
    }""")
    assert parsed == {"items": [{"name": "Bund"}]}


def test_throws_when_no_json_payload_found() -> None:
    with pytest.raises(JsonRepairError, match="No JSON payload"):
        repair_json("no structured payload")


def test_throws_when_no_complete_json_payload() -> None:
    with pytest.raises(JsonRepairError, match="No complete JSON payload"):
        extract_json_candidate('{"unterminated": "value"')


def test_extracts_array_when_array_comes_first() -> None:
    assert repair_json("Result: [1,2,3] tail") == "[1,2,3]"


def test_handles_nested_braces_inside_strings() -> None:
    raw = '{"k":"a } b { c","x":1}'
    assert parse_json_with_repair(raw) == {"k": "a } b { c", "x": 1}


def test_handles_escaped_quotes_inside_strings() -> None:
    raw = '{"msg":"He said \\"hi\\""}'
    assert parse_json_with_repair(raw) == {"msg": 'He said "hi"'}


def test_throws_on_mismatched_delimiters() -> None:
    with pytest.raises(JsonRepairError, match="Mismatched"):
        extract_json_candidate('{"a": [1, 2}')
