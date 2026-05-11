import type { PlanningSession } from "@/lib/types"
import {
  activeStayOption,
  destinationTags,
} from "./resultPageModel"

interface TripSpineProps {
  session: PlanningSession
}

export function TripSpine({ session }: TripSpineProps) {
  const constraints = session.hard_constraints
  const stay = activeStayOption(session)
  const tags = destinationTags(session)
  const transportSummary = formatTransportSummary(session)

  const facts = [
    ["Destination", constraints.destination_city],
    ["Duration", pluralize(constraints.duration_days, "day")],
    ["Travelers", pluralize(constraints.traveler_count, "traveler")],
    ["Stay area", stay?.area.name ?? "Pending"],
  ] as const

  return (
    <section
      aria-labelledby="trip-spine-title"
      className="rounded-lg border border-slate-200 bg-white p-4 sm:p-5"
    >
      <div className="flex min-w-0 flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <p className="text-sm font-medium uppercase tracking-[0.16em] text-slate-500">
            Trip spine
          </p>
          <h2
            id="trip-spine-title"
            className="mt-2 break-words text-xl font-semibold text-slate-950"
          >
            {constraints.destination_city}
          </h2>
        </div>

        {transportSummary && (
          <div className="min-w-0 border-t border-slate-200 pt-3 lg:max-w-sm lg:border-t-0 lg:pt-0">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
              Transport
            </p>
            <p className="mt-1 break-words text-sm font-medium leading-5 text-slate-800">
              {transportSummary}
            </p>
          </div>
        )}
      </div>

      <dl className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {facts.map(([label, value]) => (
          <div key={label} className="min-w-0 border-t border-slate-200 pt-3">
            <dt className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
              {label}
            </dt>
            <dd className="mt-1 break-words text-sm font-semibold text-slate-950">
              {value}
            </dd>
          </div>
        ))}
      </dl>

      <div className="mt-5 min-w-0 border-t border-slate-200 pt-4">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
          Travel tone
        </p>
        {tags.length > 0 ? (
          <div className="mt-3 flex min-w-0 flex-wrap gap-2">
            {tags.map((tag) => (
              <span
                key={tag}
                title={tag}
                className="max-w-full truncate rounded-md bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700"
              >
                {tag}
              </span>
            ))}
          </div>
        ) : (
          <p className="mt-2 break-words text-sm font-medium text-slate-700">
            Tone tags pending
          </p>
        )}
      </div>
    </section>
  )
}

function formatTransportSummary(session: PlanningSession): string | null {
  const transport = session.transport_recommendation
  if (!transport) {
    return null
  }

  const arrivalMode = formatMode(transport.arrival.mode)
  const departureMode = formatMode(transport.departure.mode)
  const intracityMode = formatMode(transport.intracity.primary_mode)

  return `${arrivalMode} arrival, ${departureMode} departure, ${intracityMode} in-city.`
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
