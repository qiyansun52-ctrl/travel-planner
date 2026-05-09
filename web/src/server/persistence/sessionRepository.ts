import {
  DiscoveryState,
  HardConstraints,
  Itinerary,
  PlanningSession,
  Preference,
  StayRecommendation,
  TransportRecommendation,
  ValidatorIssue,
} from "@/domain/schemas"

export interface SessionRepository {
  create(hardConstraints: HardConstraints): Promise<PlanningSession>
  get(sessionId: string): Promise<PlanningSession | null>
  updateDiscovery(sessionId: string, discoveryState: DiscoveryState): Promise<PlanningSession>
  updatePreferences(sessionId: string, preferences: Preference): Promise<PlanningSession>
  updateStayRecommendation(
    sessionId: string,
    stayRecommendation: StayRecommendation
  ): Promise<PlanningSession>
  updateTransportRecommendation(
    sessionId: string,
    transportRecommendation: TransportRecommendation
  ): Promise<PlanningSession>
  writeItinerary(
    sessionId: string,
    itinerary: Itinerary,
    validatorIssues: ValidatorIssue[]
  ): Promise<PlanningSession>
  appendConversationTurn(
    sessionId: string,
    turn: PlanningSession["conversation_history"][number]
  ): Promise<PlanningSession>
  updateStayOverride(sessionId: string, stayOptionId: string | null): Promise<PlanningSession>
  resetToStep(
    sessionId: string,
    step: "intake" | "discovery",
    updatedConstraints?: HardConstraints
  ): Promise<PlanningSession>
  archiveAndFork(
    sessionId: string,
    snapshotLabel: string,
    newHardConstraints: HardConstraints
  ): Promise<PlanningSession>
  updateSnapshotLabel(sessionId: string, snapshotLabel: string): Promise<PlanningSession>
}
