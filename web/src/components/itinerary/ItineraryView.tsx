"use client"

import { PlanningSession } from "@/domain/schemas"
import { ItineraryDayCard } from "./ItineraryDayCard"
import { StayAreaSwitcher } from "./StayAreaSwitcher"

interface ItineraryViewProps {
  session: PlanningSession
  onStayOverride: (stayOptionId: string | null) => Promise<void> | void
}

export function ItineraryView({ session, onStayOverride }: ItineraryViewProps) {
  const itinerary = session.itinerary
  if (!itinerary) return null

  const rows = [
    ["Transport", itinerary.budget.transport],
    ["Stay", itinerary.budget.stay],
    ["Food", itinerary.budget.food],
    ["Attractions", itinerary.budget.attractions],
    ["Other", itinerary.budget.other],
    ["Total", itinerary.budget.total],
  ] as const

  return (
    <div className="space-y-5">
      <header>
        <p className="text-sm font-medium uppercase tracking-[0.16em] text-slate-500">
          {session.hard_constraints.destination_city}
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-950">
          Your {session.hard_constraints.duration_days} day itinerary
        </h1>
      </header>

      {session.stay_recommendation && (
        <StayAreaSwitcher stay={session.stay_recommendation} onSelect={onStayOverride} />
      )}

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="text-lg font-semibold text-slate-950">Final budget</h2>
        <div className="mt-3 grid gap-2 md:grid-cols-3">
          {rows.map(([label, band]) => (
            <div key={label} className="rounded-md bg-slate-50 px-3 py-2">
              <p className="text-xs text-slate-500">{label}</p>
              <p className="mt-1 font-semibold text-slate-900">
                {band.currency} {Math.round(band.low)}-{Math.round(band.high)}
              </p>
            </div>
          ))}
        </div>
      </section>

      {itinerary.days.map((day) => (
        <ItineraryDayCard
          key={day.day_index}
          day={day}
          issues={itinerary.validator_issues.filter(
            (issue) =>
              issue.scope.type === "trip" ||
              Number(issue.scope.day_index) === day.day_index
          )}
        />
      ))}
    </div>
  )
}
