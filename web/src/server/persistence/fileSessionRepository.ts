import { randomUUID } from "node:crypto"
import { mkdir, readFile, rename, writeFile } from "node:fs/promises"
import path from "node:path"
import {
  DiscoveryState,
  HardConstraints,
  Itinerary,
  PlanningSession,
  PlanningSessionSchema,
  Preference,
  StayRecommendation,
  TransportRecommendation,
  ValidatorIssue,
} from "@/domain/schemas"
import { SessionRepository } from "./sessionRepository"

type SessionStore = Record<string, PlanningSession>

const mutationQueues = new Map<string, Promise<unknown>>()

export class FileSessionRepository implements SessionRepository {
  constructor(private readonly filePath: string) {}

  async create(hardConstraints: HardConstraints): Promise<PlanningSession> {
    return this.enqueueMutation(async () => {
      const store = await this.readStore()
      const now = new Date().toISOString()
      const session: PlanningSession = {
        session_id: `session_${randomUUID()}`,
        hard_constraints: hardConstraints,
        discovery_state: null,
        preferences: null,
        stay_recommendation: null,
        transport_recommendation: null,
        itinerary: null,
        conversation_history: [],
        validator_issues: [],
        parent_session_id: null,
        snapshot_label: null,
        status: "active",
        created_at: now,
        updated_at: now,
      }

      store[session.session_id] = session
      await this.writeStore(store)
      return session
    })
  }

  async get(sessionId: string): Promise<PlanningSession | null> {
    const store = await this.readStore()
    return store[sessionId] ?? null
  }

  async updateDiscovery(
    sessionId: string,
    discoveryState: DiscoveryState
  ): Promise<PlanningSession> {
    return this.updateActive(sessionId, (session) => ({
      ...session,
      discovery_state: discoveryState,
    }))
  }

  async updatePreferences(sessionId: string, preferences: Preference): Promise<PlanningSession> {
    return this.updateActive(sessionId, (session) => ({
      ...session,
      preferences,
    }))
  }

  async updateStayRecommendation(
    sessionId: string,
    stayRecommendation: StayRecommendation
  ): Promise<PlanningSession> {
    return this.updateActive(sessionId, (session) => ({
      ...session,
      stay_recommendation: stayRecommendation,
    }))
  }

  async updateTransportRecommendation(
    sessionId: string,
    transportRecommendation: TransportRecommendation
  ): Promise<PlanningSession> {
    return this.updateActive(sessionId, (session) => ({
      ...session,
      transport_recommendation: transportRecommendation,
    }))
  }

  async writeItinerary(
    sessionId: string,
    itinerary: Itinerary,
    validatorIssues: ValidatorIssue[]
  ): Promise<PlanningSession> {
    return this.updateActive(sessionId, (session) => ({
      ...session,
      itinerary: {
        ...itinerary,
        validator_issues: validatorIssues,
      },
      validator_issues: validatorIssues,
    }))
  }

  async appendConversationTurn(
    sessionId: string,
    turn: PlanningSession["conversation_history"][number]
  ): Promise<PlanningSession> {
    return this.updateActive(sessionId, (session) => ({
      ...session,
      conversation_history: [...session.conversation_history, turn],
    }))
  }

  async updateStayOverride(
    sessionId: string,
    stayOptionId: string | null
  ): Promise<PlanningSession> {
    return this.updateActive(sessionId, (session) => {
      if (!session.stay_recommendation) {
        throw new Error(`Session ${sessionId} has no stay recommendation`)
      }

      return {
        ...session,
        stay_recommendation: {
          ...session.stay_recommendation,
          user_override_id: stayOptionId,
        },
      }
    })
  }

  async resetToStep(
    sessionId: string,
    _step: "intake" | "discovery",
    updatedConstraints?: HardConstraints
  ): Promise<PlanningSession> {
    return this.updateActive(sessionId, (session) => ({
      ...session,
      hard_constraints: updatedConstraints ?? session.hard_constraints,
      discovery_state: null,
      preferences: null,
      stay_recommendation: null,
      transport_recommendation: null,
      itinerary: null,
      validator_issues: [],
    }))
  }

  async archiveAndFork(
    sessionId: string,
    snapshotLabel: string,
    newHardConstraints: HardConstraints
  ): Promise<PlanningSession> {
    return this.enqueueMutation(async () => {
      const store = await this.readStore()
      const original = this.requireSession(store, sessionId)
      this.assertActive(original)

      const now = new Date().toISOString()
      store[sessionId] = {
        ...original,
        status: "archived",
        snapshot_label: snapshotLabel,
        updated_at: now,
      }

      const fork: PlanningSession = {
        session_id: `session_${randomUUID()}`,
        hard_constraints: newHardConstraints,
        discovery_state: null,
        preferences: null,
        stay_recommendation: null,
        transport_recommendation: null,
        itinerary: null,
        conversation_history: [],
        validator_issues: [],
        parent_session_id: sessionId,
        snapshot_label: null,
        status: "active",
        created_at: now,
        updated_at: now,
      }

      store[fork.session_id] = fork
      await this.writeStore(store)
      return fork
    })
  }

  async updateSnapshotLabel(
    sessionId: string,
    snapshotLabel: string
  ): Promise<PlanningSession> {
    return this.enqueueMutation(async () => {
      const store = await this.readStore()
      const session = this.requireSession(store, sessionId)
      const updated = this.touch({
        ...session,
        snapshot_label: snapshotLabel,
      })

      store[sessionId] = updated
      await this.writeStore(store)
      return updated
    })
  }

  private async updateActive(
    sessionId: string,
    updater: (session: PlanningSession) => PlanningSession
  ): Promise<PlanningSession> {
    return this.enqueueMutation(async () => {
      const store = await this.readStore()
      const session = this.requireSession(store, sessionId)
      this.assertActive(session)
      const updated = this.touch(updater(session))
      store[sessionId] = updated
      await this.writeStore(store)
      return updated
    })
  }

  private async readStore(): Promise<SessionStore> {
    try {
      const content = await readFile(this.filePath, "utf8")
      const parsed = JSON.parse(content) as SessionStore
      return Object.fromEntries(
        Object.entries(parsed).map(([id, session]) => [id, PlanningSessionSchema.parse(session)])
      )
    } catch (error) {
      if (isMissingFileError(error)) return {}
      if (error instanceof SyntaxError) {
        await this.quarantineCorruptStore()
        return {}
      }
      throw error
    }
  }

  private async writeStore(store: SessionStore): Promise<void> {
    await mkdir(path.dirname(this.filePath), { recursive: true })
    const tempPath = `${this.filePath}.${process.pid}.${randomUUID()}.tmp`
    await writeFile(tempPath, `${JSON.stringify(store, null, 2)}\n`, "utf8")
    await rename(tempPath, this.filePath)
  }

  private async enqueueMutation<T>(operation: () => Promise<T>): Promise<T> {
    const previous = mutationQueues.get(this.filePath) ?? Promise.resolve()
    const next = previous.then(operation, operation)
    mutationQueues.set(
      this.filePath,
      next.catch(() => {
        // Keep the queue alive after failures so later writes are not stranded.
      })
    )
    return next
  }

  private async quarantineCorruptStore(): Promise<void> {
    const corruptPath = `${this.filePath}.corrupt-${Date.now()}`
    try {
      await rename(this.filePath, corruptPath)
    } catch {
      // If another request already handled the corrupt file, continue with an empty store.
    }
  }

  private requireSession(store: SessionStore, sessionId: string): PlanningSession {
    const session = store[sessionId]
    if (!session) throw new Error(`Session ${sessionId} not found`)
    return session
  }

  private assertActive(session: PlanningSession): void {
    if (session.status === "archived") {
      throw new Error(`Session ${session.session_id} is archived`)
    }
  }

  private touch(session: PlanningSession): PlanningSession {
    return {
      ...session,
      updated_at: new Date().toISOString(),
    }
  }
}

let defaultRepository: FileSessionRepository | null = null

export function getDefaultSessionRepository(): FileSessionRepository {
  defaultRepository ??= new FileSessionRepository(path.join(process.cwd(), ".data/sessions.json"))
  return defaultRepository
}

function isMissingFileError(error: unknown): boolean {
  return (
    typeof error === "object" &&
    error !== null &&
    "code" in error &&
    (error as { code: unknown }).code === "ENOENT"
  )
}
