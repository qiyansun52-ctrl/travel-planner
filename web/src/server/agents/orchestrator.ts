import { validateItinerary } from "@/domain/validator"
import {
  Itinerary,
  PlanningSession,
  StayRecommendation,
  TransportRecommendation,
  ValidatorIssue,
} from "@/domain/schemas"
import { runPlannerAgent } from "./planner"
import { runStayAgent } from "./stay"
import { runTransportAgent } from "./transport"

export interface PlanningResult {
  stay: StayRecommendation
  transport: TransportRecommendation
  itinerary: Itinerary
  validatorIssues: ValidatorIssue[]
}

interface PlanningOrchestratorDependencies {
  runStayAgent: (session: PlanningSession) => Promise<StayRecommendation>
  runTransportAgent: (session: PlanningSession) => Promise<TransportRecommendation>
  runPlannerAgent: (
    session: PlanningSession,
    stay: StayRecommendation,
    transport: TransportRecommendation,
    validatorIssues?: ValidatorIssue[]
  ) => Promise<Itinerary>
  validate: (itinerary: Itinerary, session: PlanningSession) => ValidatorIssue[]
}

export function createPlanningOrchestrator(
  dependencies: PlanningOrchestratorDependencies
) {
  return {
    async runFullPlanning(session: PlanningSession): Promise<PlanningResult> {
      const stay = await dependencies.runStayAgent(session)
      const transport = await dependencies.runTransportAgent(session)
      return runPlannerWithCorrectivePass(session, stay, transport, dependencies)
    },

    async runPlannerOnly(
      session: PlanningSession,
      reason: string
    ): Promise<PlanningResult> {
      void reason
      if (!session.stay_recommendation || !session.transport_recommendation) {
        throw new Error("Planner-only runs require existing stay and transport outputs")
      }
      return runPlannerWithCorrectivePass(
        session,
        session.stay_recommendation,
        session.transport_recommendation,
        dependencies
      )
    },
  }
}

export const planningOrchestrator = createPlanningOrchestrator({
  runStayAgent,
  runTransportAgent,
  runPlannerAgent,
  validate: (itinerary, session) =>
    validateItinerary(itinerary, {
      discoveryCards: session.discovery_state?.payload?.cards ?? [],
    }),
})

async function runPlannerWithCorrectivePass(
  session: PlanningSession,
  stay: StayRecommendation,
  transport: TransportRecommendation,
  dependencies: PlanningOrchestratorDependencies
): Promise<PlanningResult> {
  const first = await dependencies.runPlannerAgent(session, stay, transport)
  const firstIssues = dependencies.validate(first, session)
  const errors = firstIssues.filter((issue) => issue.severity === "error")

  if (errors.length === 0) {
    const itinerary = { ...first, validator_issues: firstIssues }
    return { stay, transport, itinerary, validatorIssues: firstIssues }
  }

  const second = await dependencies.runPlannerAgent(session, stay, transport, errors)
  const secondIssues = dependencies.validate(second, session)
  const itinerary = { ...second, validator_issues: secondIssues }
  return { stay, transport, itinerary, validatorIssues: secondIssues }
}
