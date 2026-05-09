"use client"

import { useEffect, useState } from "react"
import { listSessions } from "@/lib/apiClient"
import type { PlanningSession } from "@/lib/types"
import { HardConstraintForm, type IntakeLanguage } from "./HardConstraintForm"
import { RecentTrips } from "./RecentTrips"

const copy = {
  en: {
    eyebrow: "Single-city travel planning",
    title: "Plan a single-city trip",
    body: "Start with constraints, discover what is worth doing, then shape the stay, transport, and itinerary.",
    switchLabel: "切换到中文",
    switchText: "中文",
  },
  zh: {
    eyebrow: "单城市旅行规划",
    title: "规划一趟单城市旅行",
    body: "先填写硬性条件，再发现值得体验的内容，最后生成住宿、交通和每日行程。",
    switchLabel: "Switch to English",
    switchText: "EN",
  },
} satisfies Record<IntakeLanguage, Record<string, string>>

export function HomeStart() {
  const [language, setLanguage] = useState<IntakeLanguage>("en")
  const [recentSessions, setRecentSessions] = useState<PlanningSession[]>([])
  const text = copy[language]

  useEffect(() => {
    let active = true
    listSessions()
      .then((sessions) => {
        if (active) setRecentSessions(sessions)
      })
      .catch(() => {
        if (active) setRecentSessions([])
      })
    return () => {
      active = false
    }
  }, [])

  return (
    <section className="mx-auto flex min-h-[calc(100vh-4rem)] w-full max-w-6xl flex-col justify-center gap-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="mb-3 text-sm font-medium uppercase tracking-[0.16em] text-slate-500">
            {text.eyebrow}
          </p>
          <h1 className="max-w-3xl text-4xl font-semibold leading-tight sm:text-5xl">
            {text.title}
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-slate-600">
            {text.body}
          </p>
        </div>
        <button
          type="button"
          aria-label={text.switchLabel}
          onClick={() => setLanguage((current) => (current === "en" ? "zh" : "en"))}
          className="h-10 shrink-0 rounded-md border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-800 hover:bg-slate-100"
        >
          {text.switchText}
        </button>
      </div>
      <RecentTrips sessions={recentSessions} language={language} />
      <HardConstraintForm language={language} />
    </section>
  )
}
