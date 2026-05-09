"use client"

import Link from "next/link"
import type { PlanningSession } from "@/lib/types"
import type { IntakeLanguage } from "./HardConstraintForm"

const copy = {
  en: {
    title: "Recent trips",
    resume: "Resume",
    itineraryReady: "Itinerary ready",
    preferencesReady: "Ready to plan",
    discoveryReady: "Discovery ready",
    justStarted: "Just started",
    updated: "Updated",
    days: "days",
  },
  zh: {
    title: "最近行程",
    resume: "继续",
    itineraryReady: "行程已生成",
    preferencesReady: "可生成行程",
    discoveryReady: "已完成发现",
    justStarted: "刚开始",
    updated: "更新于",
    days: "天",
  },
} satisfies Record<IntakeLanguage, Record<string, string>>

export function RecentTrips({
  sessions,
  language,
}: {
  sessions: PlanningSession[]
  language: IntakeLanguage
}) {
  if (sessions.length === 0) return null
  const text = copy[language]

  return (
    <section aria-labelledby="recent-trips-title" className="w-full max-w-5xl">
      <div className="mb-3 flex items-center justify-between">
        <h2 id="recent-trips-title" className="text-sm font-semibold text-slate-900">
          {text.title}
        </h2>
      </div>
      <div className="grid gap-2">
        {sessions.map((session) => (
          <article
            key={session.session_id}
            className="grid gap-3 rounded-md border border-slate-200 bg-white px-4 py-3 shadow-sm sm:grid-cols-[1fr_auto] sm:items-center"
          >
            <div className="min-w-0">
              <h3 className="truncate text-sm font-semibold text-slate-950">
                {session.hard_constraints.destination_city}
              </h3>
              <p className="mt-1 text-sm text-slate-600">
                {session.hard_constraints.departure_date} ·{" "}
                {session.hard_constraints.duration_days} {text.days} ·{" "}
                {session.hard_constraints.currency}{" "}
                {session.hard_constraints.total_budget}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                {tripStatus(session, text)} · {text.updated}{" "}
                {formatUpdatedAt(session.updated_at)}
              </p>
            </div>
            <Link
              href={resumeHref(session)}
              className="inline-flex h-9 items-center justify-center rounded-md bg-slate-950 px-3 text-sm font-semibold text-white hover:bg-slate-800"
            >
              {text.resume}
            </Link>
          </article>
        ))}
      </div>
    </section>
  )
}

export function resumeHref(session: PlanningSession): string {
  if (session.itinerary || session.preferences) {
    return `/trips/${session.session_id}`
  }
  if ((session.discovery_state?.selected_card_ids?.length ?? 0) > 0) {
    return `/preferences/${session.session_id}`
  }
  return `/discovery/${session.session_id}`
}

function tripStatus(session: PlanningSession, text: Record<string, string>): string {
  if (session.itinerary) return text.itineraryReady
  if (session.preferences) return text.preferencesReady
  if (session.discovery_state?.payload) return text.discoveryReady
  return text.justStarted
}

function formatUpdatedAt(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value))
}
