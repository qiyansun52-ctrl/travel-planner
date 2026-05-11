import type { ReactNode } from "react"
import type { PlanningSession } from "@/lib/types"
import {
  activeStayOption,
  smartAdjustmentPrompts,
} from "./resultPageModel"

interface CompanionRailProps {
  session: PlanningSession
  adjustmentPanel?: ReactNode
}

export function CompanionRail({ session, adjustmentPanel }: CompanionRailProps) {
  const stay = activeStayOption(session)
  const prompts = smartAdjustmentPrompts(session)
  const mappedPlaces = countMappedPlaces(session)
  const totalPlaces = countPlaceSegments(session)
  const constraints = session.hard_constraints

  return (
    <aside className="space-y-4">
      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <p className="text-sm font-medium uppercase tracking-[0.16em] text-slate-500">
          Spatial brief
        </p>
        <div className="mt-4 space-y-3">
          <BriefRow
            label="Mapped places"
            value={
              totalPlaces > 0
                ? `${mappedPlaces} of ${totalPlaces} with coordinates`
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

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <p className="text-sm font-medium uppercase tracking-[0.16em] text-slate-500">
          Companion brief
        </p>
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
        <section className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="text-sm font-medium uppercase tracking-[0.16em] text-slate-500">
            Smart adjustments
          </p>
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

function countMappedPlaces(session: PlanningSession): number {
  return (
    session.itinerary?.days.reduce(
      (count, day) =>
        count + day.segments.filter((segment) => Boolean(segment.place?.coordinate)).length,
      0,
    ) ?? 0
  )
}

function countPlaceSegments(session: PlanningSession): number {
  return (
    session.itinerary?.days.reduce(
      (count, day) => count + day.segments.filter((segment) => Boolean(segment.place)).length,
      0,
    ) ?? 0
  )
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
