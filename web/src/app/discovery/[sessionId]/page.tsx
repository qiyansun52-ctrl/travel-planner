"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { DiscoveryBoard } from "@/components/discovery/DiscoveryBoard"
import { PlanningSession } from "@/domain/schemas"
import { getSession, runDiscovery, updateSelectedCards } from "@/lib/apiClient"

export default function DiscoveryPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const router = useRouter()
  const [session, setSession] = useState<PlanningSession | null>(null)
  const [error, setError] = useState("")

  useEffect(() => {
    let active = true
    async function load() {
      try {
        const current = await getSession(sessionId)
        const withDiscovery = current.discovery_state?.payload
          ? current
          : await runDiscovery(sessionId)
        if (active) setSession(withDiscovery)
      } catch (loadError) {
        if (active) setError(loadError instanceof Error ? loadError.message : "Discovery failed")
      }
    }
    void load()
    return () => {
      active = false
    }
  }, [sessionId])

  if (error) return <Centered message={error} />
  if (!session?.discovery_state?.payload) return <Centered message="Preparing discovery..." />

  return (
    <DiscoveryBoard
      session={session}
      output={session.discovery_state.payload}
      onSelectionChange={async (ids) => {
        const updated = await updateSelectedCards(sessionId, ids)
        setSession(updated)
      }}
      onContinue={async (ids) => {
        await updateSelectedCards(sessionId, ids)
        router.push(`/preferences/${sessionId}`)
      }}
    />
  )
}

function Centered({ message }: { message: string }) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-5 text-slate-700">
      {message}
    </main>
  )
}
