# Agent Optimization Plan

> Status: implemented foundation on 2026-05-13.

## Scope

This plan applies only to this Travel Planner codebase. `TripStar/` is external and is not part of the optimization target.

The current product already has a useful fixed workflow:

```text
discovery -> stay -> transport -> planner -> validator -> corrective planner
```

The right next step is not to add a broad autonomous supervisor. The current problem is agent handoff quality: each stage should make its responsibility explicit, preserve useful signals for later stages, and expose deterministic quality reports so regressions are visible.

## References

- Anthropic, "Building effective agents": keep agent systems simple, transparent, and evaluated before adding autonomy.
  https://www.anthropic.com/engineering/building-effective-agents
- LangChain/LangGraph handoffs docs: handoffs are useful for sequential, stateful, multi-stage flows.
  https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs
- OpenAI Agents SDK guardrails docs: guardrails should be attached at workflow/tool boundaries when multiple specialists or handoffs exist.
  https://openai.github.io/openai-agents-python/guardrails/
- OpenAI Agents SDK tracing docs: production agent runs should expose spans for agents, tool calls, guardrails, and handoffs.
  https://github.com/openai/openai-agents-python/blob/main/docs/tracing.md
- LangGraph generative UI examples, Trip Planner Agent: travel agents benefit from typed state, extraction, routing, and UI-visible planning progress.
  https://github.com/langchain-ai/langgraphjs-gen-ui-examples
- Embabel Tripper: travel planning agents can stay maintainable by centering the domain model and deterministic planning around external tools.
  https://github.com/embabel/tripper

## Implemented Changes

1. Added `api/app/graph/agent_contracts.py`.
   - Defines stable contracts for `discovery`, `stay`, `transport`, `planner`, and `validator`.
   - Each contract declares responsibility, required inputs, produced outputs, handoff targets, and quality gates.
   - Progress events now include compact agent metadata and a contract version.

2. Added deterministic quality reports.
   - Discovery report: card count, source count, enrichment depth, place/cost coverage, reservation hints.
   - Planner report: day count, segment count, mapped attraction coverage, reservation notes, budget overrun flag.
   - Validator report: issue counts by severity and issue codes.

3. Improved agent handoff behavior.
   - Planner now carries `DiscoveryCard.reservation_hint` into itinerary day notes as a reservation check.
   - This prevents useful discovery-stage travel intelligence from disappearing before the final plan.

4. Added tests.
   - Agent contract tests cover stage coverage, JSON serializability, and quality report shape.
   - Node tests assert progress payloads now include agent metadata and planner reservation handoff.

## Next Iterations

1. Upgrade the validator from budget-only checks toward day-quality checks from Plan20:
   - too empty,
   - too dense,
   - missing meal rhythm,
   - risky reservation/opening-hour dependency.

2. Add a source-bundle grounding layer before discovery/stay/transport:
   - Tavily search plus extract,
   - source dedupe,
   - compact source summaries,
   - image provenance.

3. Add an offline eval fixture set:
   - one easy city,
   - one budget-constrained trip,
   - one reservation-heavy trip,
   - one sparse-discovery fallback trip.

4. Surface selected quality metrics in the UI only where they help users understand progress.
