"""Agent contracts and deterministic quality reports for graph handoffs."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Literal

from app.models.schemas import DiscoveryOutput, Itinerary, ValidatorIssue

AgentStage = Literal["discovery", "stay", "transport", "planner", "validator"]
CONTRACT_VERSION = "2026-05-13"


@dataclass(frozen=True, slots=True)
class AgentContract:
    stage: AgentStage
    name: str
    responsibility: str
    handoff_to: tuple[str, ...]
    required_inputs: tuple[str, ...]
    produced_outputs: tuple[str, ...]
    quality_gates: tuple[str, ...]

    def progress_metadata(self) -> dict[str, object]:
        return {
            "stage": self.stage,
            "name": self.name,
            "contract_version": CONTRACT_VERSION,
            "responsibility": self.responsibility,
            "handoff_to": list(self.handoff_to),
            "quality_gates": list(self.quality_gates),
        }


AGENT_CONTRACTS: dict[AgentStage, AgentContract] = {
    "discovery": AgentContract(
        stage="discovery",
        name="Discovery research agent",
        responsibility="Produce grounded interest cards, area signals, food signals, and source notes.",
        handoff_to=("stay", "transport", "planner"),
        required_inputs=("hard_constraints", "optional_search_grounding"),
        produced_outputs=("DiscoveryOutput",),
        quality_gates=(
            "at least three discovery cards",
            "source notes retained when grounding exists",
            "enrichment status available for every card",
        ),
    ),
    "stay": AgentContract(
        stage="stay",
        name="Stay recommendation agent",
        responsibility="Choose the active stay area and alternatives from discovery area signals.",
        handoff_to=("planner",),
        required_inputs=("hard_constraints", "discovery_area_summaries", "preferences"),
        produced_outputs=("StayRecommendation",),
        quality_gates=(
            "primary stay option exists",
            "alternatives preserved for user override",
        ),
    ),
    "transport": AgentContract(
        stage="transport",
        name="Transport recommendation agent",
        responsibility="Recommend arrival, departure, and local movement strategy.",
        handoff_to=("planner",),
        required_inputs=("hard_constraints", "preferences"),
        produced_outputs=("TransportRecommendation",),
        quality_gates=(
            "arrival and departure modes exist",
            "intracity daily cost band exists",
        ),
    ),
    "planner": AgentContract(
        stage="planner",
        name="Itinerary planning agent",
        responsibility="Merge selected interests, stay, transport, budget, and validator feedback into daily plans.",
        handoff_to=("validator",),
        required_inputs=(
            "selected_discovery_cards",
            "stay_recommendation",
            "transport_recommendation",
            "validator_issues",
        ),
        produced_outputs=("Itinerary",),
        quality_gates=(
            "day count matches requested duration",
            "selected discovery cards are represented as itinerary segments",
            "reservation hints are preserved as day notes",
        ),
    ),
    "validator": AgentContract(
        stage="validator",
        name="Deterministic itinerary validator",
        responsibility="Evaluate budget and feasibility issues without rewriting the itinerary.",
        handoff_to=("planner", "user"),
        required_inputs=("itinerary", "discovery_cards"),
        produced_outputs=("ValidatorIssue[]",),
        quality_gates=(
            "issues are structured by severity",
            "error issues can trigger one corrective planner pass",
        ),
    ),
}


def agent_progress_payload(stage: AgentStage, **details: Any) -> dict[str, Any]:
    return {"agent": AGENT_CONTRACTS[stage].progress_metadata(), **details}


def discovery_quality_report(output: DiscoveryOutput) -> dict[str, object]:
    status_counts = Counter(card.enrichment_status for card in output.cards)
    card_count = len(output.cards)
    source_note_count = len(output.source_notes)
    return {
        "card_count": card_count,
        "source_note_count": source_note_count,
        "complete_card_count": status_counts["complete"],
        "partial_card_count": status_counts["partial"],
        "minimal_card_count": status_counts["minimal"],
        "cards_with_place_count": sum(card.place is not None for card in output.cards),
        "cards_with_cost_estimate_count": sum(
            card.cost_estimate is not None for card in output.cards
        ),
        "reservation_hint_count": sum(
            bool(card.reservation_hint) for card in output.cards
        ),
        "min_cards_met": card_count >= 3,
        "has_grounding": source_note_count > 0,
    }


def itinerary_quality_report(
    itinerary: Itinerary,
    *,
    expected_day_count: int,
) -> dict[str, object]:
    segments = [segment for day in itinerary.days for segment in day.segments]
    attraction_segments = [
        segment for segment in segments if segment.type == "attraction"
    ]
    return {
        "day_count": len(itinerary.days),
        "expected_day_count": expected_day_count,
        "day_count_matches_duration": len(itinerary.days) == expected_day_count,
        "segment_count": len(segments),
        "attraction_segment_count": len(attraction_segments),
        "mapped_attraction_segment_count": sum(
            segment.place is not None for segment in attraction_segments
        ),
        "transit_segment_count": sum(segment.type == "transit" for segment in segments),
        "reservation_note_count": sum(
            "Reservation check:" in note for day in itinerary.days for note in day.notes
        ),
        "budget_overrun_flag": itinerary.budget.overrun_flag,
        "validator_issue_count": len(itinerary.validator_issues),
    }


def validator_quality_report(issues: list[ValidatorIssue]) -> dict[str, object]:
    return {
        "issue_count": len(issues),
        "error_count": sum(issue.severity == "error" for issue in issues),
        "warning_count": sum(issue.severity == "warning" for issue in issues),
        "issue_codes": [issue.code for issue in issues],
    }
