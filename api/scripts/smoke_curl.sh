#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

SESSION_JSON="$(curl -fsS -X POST "$BASE_URL/api/sessions" \
  -H 'Content-Type: application/json' \
  -d '{"departure_city":"杭州","destination_city":"上海","destination_country_code":"CN","departure_date":"2026-06-01","duration_days":3,"traveler_count":2,"total_budget":6000,"currency":"CNY"}')"

SESSION_ID="$("$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["session_id"])' <<<"$SESSION_JSON")"

DISCOVERY_JSON="$(curl -fsS -X POST "$BASE_URL/api/sessions/$SESSION_ID/discovery")"
SELECTED_CARD_IDS="$("$PYTHON_BIN" -c 'import json,sys; cards=json.load(sys.stdin)["discovery_state"]["payload"]["cards"]; print(json.dumps([card["id"] for card in cards[:3]]))' <<<"$DISCOVERY_JSON")"

curl -fsS -X PATCH "$BASE_URL/api/sessions/$SESSION_ID/selection" \
  -H 'Content-Type: application/json' \
  -d "{\"selected_card_ids\":$SELECTED_CARD_IDS}" >/dev/null
curl -fsS -X POST "$BASE_URL/api/sessions/$SESSION_ID/preferences" \
  -H 'Content-Type: application/json' \
  -d '{"preferences":{"area_vibe":"central and walkable","quiet_vs_lively":"balanced","stay_type":"hotel","willing_to_change_hotels":false,"intercity_transport_preference":"rail","early_departure_tolerance":"medium","transfer_tolerance":"medium","pay_more_to_save_time":true}}' >/dev/null
curl -fsS -X POST "$BASE_URL/api/sessions/$SESSION_ID/itinerary" \
  -H 'Content-Type: application/json' \
  -d '{}' >/dev/null
curl -fsS -X POST "$BASE_URL/api/sessions/$SESSION_ID/adjustments" \
  -H 'Content-Type: application/json' \
  -d '{"message":"Update the itinerary for day two."}' >/dev/null

echo "Smoke flow passed for $SESSION_ID"
