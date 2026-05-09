"""LangGraph planning workflows."""

from __future__ import annotations

from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.graph.nodes.planner import run_planner_node
from app.graph.nodes.stay import run_stay_node
from app.graph.nodes.transport import run_transport_node
from app.graph.nodes.validator import run_validator_node
from app.graph.state import (
    GraphState,
    PlanningGraphResult,
    PlanState,
    graph_input_from_state,
    validate_graph_state,
)
from app.models.schemas import PlanningSession

RouteName = Literal["prepare_corrective", "end"]


async def prepare_corrective_node(state: GraphState) -> GraphState:
    parsed = validate_graph_state(state)
    return GraphState(
        corrective_attempts=parsed.corrective_attempts + 1,
        validator_issues=[
            issue.model_dump(mode="json") for issue in parsed.validator_issues
        ],
    )


def route_after_validation(state: GraphState) -> RouteName:
    parsed = validate_graph_state(state)
    if parsed.has_validator_errors and parsed.corrective_attempts < 1:
        return "prepare_corrective"
    return "end"


def create_planning_graph():
    graph = StateGraph(GraphState)
    graph.add_node("stay", run_stay_node)
    graph.add_node("transport", run_transport_node)
    graph.add_node("planner", run_planner_node)
    graph.add_node("validator", run_validator_node)
    graph.add_node("prepare_corrective", prepare_corrective_node)

    graph.add_edge(START, "stay")
    graph.add_edge("stay", "transport")
    graph.add_edge("transport", "planner")
    graph.add_edge("planner", "validator")
    graph.add_conditional_edges(
        "validator",
        route_after_validation,
        {"prepare_corrective": "prepare_corrective", "end": END},
    )
    graph.add_edge("prepare_corrective", "planner")
    return graph.compile()


def create_planner_only_graph():
    graph = StateGraph(GraphState)
    graph.add_node("planner", run_planner_node)
    graph.add_node("validator", run_validator_node)
    graph.add_node("prepare_corrective", prepare_corrective_node)

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "validator")
    graph.add_conditional_edges(
        "validator",
        route_after_validation,
        {"prepare_corrective": "prepare_corrective", "end": END},
    )
    graph.add_edge("prepare_corrective", "planner")
    return graph.compile()


async def run_full_planning_workflow(session: PlanningSession) -> PlanningGraphResult:
    initial = PlanState(session=session, mode="full_planning")
    graph = create_planning_graph()
    final = await graph.ainvoke(graph_input_from_state(initial))
    return _planning_result(final)


async def run_planner_only_workflow(
    session: PlanningSession,
    *,
    reason: str,
) -> PlanningGraphResult:
    if session.stay_recommendation is None or session.transport_recommendation is None:
        raise ValueError("planner-only workflow requires existing stay and transport")

    initial = PlanState(
        session=session,
        mode="planner_only",
        planner_only_reason=reason,
        stay_recommendation=session.stay_recommendation,
        transport_recommendation=session.transport_recommendation,
    )
    graph = create_planner_only_graph()
    final = await graph.ainvoke(graph_input_from_state(initial))
    return _planning_result(final)


def _planning_result(state: GraphState) -> PlanningGraphResult:
    parsed = validate_graph_state(state)
    if parsed.stay_recommendation is None:
        raise ValueError("planning workflow finished without stay recommendation")
    if parsed.transport_recommendation is None:
        raise ValueError("planning workflow finished without transport recommendation")
    if parsed.itinerary is None:
        raise ValueError("planning workflow finished without itinerary")

    itinerary = parsed.itinerary.model_copy(update={"validator_issues": parsed.validator_issues})
    return PlanningGraphResult(
        session_id=parsed.session.session_id,
        stay=parsed.stay_recommendation,
        transport=parsed.transport_recommendation,
        itinerary=itinerary,
        validator_issues=parsed.validator_issues,
        progress_events=parsed.progress_events,
    )
