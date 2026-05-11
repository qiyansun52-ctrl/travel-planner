import type { ReactNode } from "react"
import type { ItinerarySegment, NormalizedPlace, PlanningSession } from "@/lib/types"
import {
  activeStayOption,
  smartAdjustmentPrompts,
} from "./resultPageModel"

const ROUTE_PLACE_SEGMENT_TYPES = new Set<ItinerarySegment["type"]>([
  "attraction",
  "hotel_checkin",
  "hotel_return",
])

interface CompanionRailProps {
  session: PlanningSession
  adjustmentPanel?: ReactNode
}

export function CompanionRail({ session, adjustmentPanel }: CompanionRailProps) {
  const stay = activeStayOption(session)
  const prompts = smartAdjustmentPrompts(session)
  const routePlaces = summarizeRoutePlaces(session)
  const constraints = session.hard_constraints

  return (
    <aside className="space-y-4">
      <section
        aria-labelledby="companion-rail-spatial-brief"
        className="rounded-lg border border-slate-200 bg-white p-4"
      >
        <h2
          id="companion-rail-spatial-brief"
          className="text-sm font-medium uppercase tracking-[0.16em] text-slate-500"
        >
          Spatial brief
        </h2>
        <div className="mt-4 space-y-3">
          <BriefRow
            label="Mapped places"
            value={
              routePlaces.total > 0
                ? `${routePlaces.mapped} of ${routePlaces.total} with coordinates`
                : "No mapped places yet"
            }
          />
          {stay && (
            <BriefRow
              label="Stay base"
              value={stay.area.name}
              detail={stay.fit_reason}
            />
          )}
          {session.transport_recommendation && (
            <BriefRow
              label="Local movement"
              value={formatMode(session.transport_recommendation.intracity.primary_mode)}
              detail={session.transport_recommendation.intracity.note ?? undefined}
            />
          )}
        </div>
      </section>

      <section
        aria-labelledby="companion-rail-companion-brief"
        className="rounded-lg border border-slate-200 bg-white p-4"
      >
        <h2
          id="companion-rail-companion-brief"
          className="text-sm font-medium uppercase tracking-[0.16em] text-slate-500"
        >
          Companion brief
        </h2>
        <div className="mt-4 space-y-3">
          <BriefRow label="Destination" value={constraints.destination_city} />
          <BriefRow
            label="Trip shape"
            value={`${pluralize(constraints.duration_days, "day")} for ${pluralize(
              constraints.traveler_count,
              "traveler",
            )}`}
          />
          <BriefRow
            label="Budget"
            value={formatBudget(constraints.currency, constraints.total_budget)}
          />
        </div>
      </section>

      {prompts.length > 0 && (
        <section
          aria-labelledby="companion-rail-smart-adjustments"
          className="rounded-lg border border-slate-200 bg-white p-4"
        >
          <h2
            id="companion-rail-smart-adjustments"
            className="text-sm font-medium uppercase tracking-[0.16em] text-slate-500"
          >
            Smart adjustments
          </h2>
          <ul className="mt-4 space-y-2">
            {prompts.map((prompt) => (
              <li
                key={prompt}
                className="break-words rounded-md bg-slate-50 px-3 py-2 text-sm font-medium leading-5 text-slate-700"
              >
                {prompt}
              </li>
            ))}
          </ul>
        </section>
      )}

      {adjustmentPanel}
    </aside>
  )
}

function BriefRow({
  detail,
  label,
  value,
}: {
  detail?: string
  label: string
  value: string
}) {
  return (
    <div className="min-w-0 border-t border-slate-200 pt-3 first:border-t-0 first:pt-0">
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
        {label}
      </p>
      <p className="mt-1 break-words text-sm font-semibold text-slate-950">{value}</p>
      {detail && <p className="mt-1 break-words text-sm leading-5 text-slate-600">{detail}</p>}
    </div>
  )
}

function summarizeRoutePlaces(session: PlanningSession): { mapped: number; total: number } {
  const totalKeys = new Set<string>()
  const mappedKeys = new Set<string>()

  for (const day of session.itinerary?.days ?? []) {
    for (const segment of day.segments) {
      if (!ROUTE_PLACE_SEGMENT_TYPES.has(segment.type)) {
        continue
      }

      const key = segment.place
        ? routePlaceKey(segment.place)
        : routeSegmentKey(day.day_index, segment)

      totalKeys.add(key)

      if (segment.place?.coordinate) {
        mappedKeys.add(key)
      }
    }
  }

  return {
    mapped: mappedKeys.size,
    total: totalKeys.size,
  }
}

function routePlaceKey(place: NormalizedPlace): string {
  if (place.id) {
    return `id:${place.id}`
  }

  if (place.coordinate) {
    return `coordinate:${place.coordinate.lat},${place.coordinate.lng}`
  }

  return `name:${place.name}`
}

function routeSegmentKey(dayIndex: number, segment: ItinerarySegment): string {
  return [
    "segment",
    dayIndex,
    segment.type,
    segment.start_time,
    segment.end_time,
    segment.card_ref ?? "no-card",
  ].join(":")
}

function formatBudget(currency: string, value: number): string {
  if (value <= 0) {
    return "Budget pending"
  }

  return `${currency} ${Math.round(value).toLocaleString("en-US")}`
}

function formatMode(value: string): string {
  return value
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ")
}

function pluralize(count: number, singular: string): string {
  return `${count} ${singular}${count === 1 ? "" : "s"}`
}
