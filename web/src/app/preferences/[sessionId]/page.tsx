"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { PreferenceForm } from "@/components/preferences/PreferenceForm"
import { getSession, savePreferences } from "@/lib/apiClient"
import type { PlanningSession, Preference } from "@/lib/types"

export default function PreferencesPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const router = useRouter()
  const [session, setSession] = useState<PlanningSession | null>(null)
  const [error, setError] = useState("")

  useEffect(() => {
    getSession(sessionId).then(setSession).catch((err: Error) => setError(err.message))
  }, [sessionId])

  async function handleSubmit(preferences: Preference) {
    await savePreferences(sessionId, preferences)
    router.push(`/trips/${sessionId}`)
  }

  if (error) return <Centered message={error} />
  if (!session) return <Centered message="正在加载偏好设置..." />

  return (
    <main className="min-h-screen bg-slate-50 px-5 py-8 text-slate-950">
      <section className="mx-auto flex w-full max-w-5xl flex-col gap-6">
        <div>
          <p className="text-sm font-semibold uppercase text-teal-700">
            {session.hard_constraints.destination_city}
          </p>
          <h1 className="mt-2 text-3xl font-semibold">设置住宿与交通偏好</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
            这些选择会影响住宿区域、城际交通和每日节奏。保持默认也可以，系统会按已选体验生成一版均衡方案。
          </p>
        </div>
        <PreferenceForm onSubmit={handleSubmit} />
      </section>
    </main>
  )
}

function Centered({ message }: { message: string }) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-5 text-slate-700">
      {message}
    </main>
  )
}
