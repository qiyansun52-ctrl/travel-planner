"use client"

import { useEffect, useRef, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { DiscoveryBoard } from "@/components/discovery/DiscoveryBoard"
import { getSession, runDiscovery, updateSelectedCards } from "@/lib/apiClient"
import type { PlanningSession } from "@/lib/types"

export default function DiscoveryPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const router = useRouter()
  const [session, setSession] = useState<PlanningSession | null>(null)
  const [error, setError] = useState("")
  const loadRef = useRef<{ sessionId: string; promise: Promise<PlanningSession> } | null>(null)

  useEffect(() => {
    let active = true

    async function createLoadPromise() {
      const current = await getSession(sessionId)
      return current.discovery_state?.payload ? current : await runDiscovery(sessionId)
    }

    const existing = loadRef.current
    const promise =
      existing?.sessionId === sessionId
        ? existing.promise
        : createLoadPromise()
    loadRef.current = { sessionId, promise }

    promise
      .then((withDiscovery) => {
        if (active) {
          setError("")
          setSession(withDiscovery)
        }
      })
      .catch((loadError) => {
        if (active) {
          setError(loadError instanceof Error ? loadError.message : "Discovery failed")
        }
      })

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
