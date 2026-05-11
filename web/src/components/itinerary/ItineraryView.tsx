"use client"

import type { ReactNode } from "react"
import type { PlanningSession } from "@/lib/types"
import { CompanionRail } from "./CompanionRail"
import { ItineraryDayCard } from "./ItineraryDayCard"
import { NarrativeRoute } from "./NarrativeRoute"
import { ResultHero } from "./ResultHero"
import { ResultMetrics } from "./ResultMetrics"
import {
  commandMetrics,
  narrativeRouteItems,
} from "./resultPageModel"
import { StayAreaSwitcher } from "./StayAreaSwitcher"
import { TripSpine } from "./TripSpine"

interface ItineraryViewProps {
  adjustmentPanel?: ReactNode
  session: PlanningSession
  onStayOverride: (stayOptionId: string | null) => Promise<void> | void
}

export function ItineraryView({
  adjustmentPanel,
  session,
  onStayOverride,
}: ItineraryViewProps) {
  const itinerary = session.itinerary
  if (!itinerary) return null

  return (
    <div className="space-y-6">
      <ResultHero session={session} />

      <div className="grid min-w-0 gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="min-w-0 xl:col-start-1">
          <TripSpine session={session} />
        </div>

        <div className="min-w-0 space-y-5 xl:col-start-1">
          <ResultMetrics metrics={commandMetrics(session)} />

          {session.stay_recommendation && (
            <StayAreaSwitcher stay={session.stay_recommendation} onSelect={onStayOverride} />
          )}

          <NarrativeRoute items={narrativeRouteItems(session)} />

          <section
            aria-labelledby="detailed-itinerary-title"
            className="min-w-0 space-y-4"
          >
            <div className="min-w-0">
              <p className="text-sm font-medium uppercase text-slate-500">
                Day-by-day execution
              </p>
              <h2
                id="detailed-itinerary-title"
                className="mt-2 break-words text-2xl font-semibold text-slate-950"
              >
                Detailed itinerary
              </h2>
            </div>

            <div className="space-y-4">
              {itinerary.days.map((day) => (
                <ItineraryDayCard
                  key={day.day_index}
                  day={day}
                  issues={itinerary.validator_issues.filter(
                    (issue) =>
                      issue.scope.type === "trip" ||
                      Number(issue.scope.day_index) === day.day_index,
                  )}
                />
              ))}
            </div>
          </section>
        </div>

        <div className="min-w-0 xl:col-start-2 xl:row-span-2 xl:row-start-1">
          <div className="xl:sticky xl:top-6">
            <CompanionRail session={session} adjustmentPanel={adjustmentPanel} />
          </div>
        </div>
      </div>
    </div>
  )
}
