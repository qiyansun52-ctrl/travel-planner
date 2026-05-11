"use client"

import { useEffect, useState } from "react"
import { useParams } from "next/navigation"
import { AdjustmentPanel } from "@/components/chat/AdjustmentPanel"
import { ItineraryView } from "@/components/itinerary/ItineraryView"
import { PlanningProgress } from "@/components/itinerary/PlanningProgress"
import { getSession, streamItinerary, updateStayOverride } from "@/lib/apiClient"
import type { PlanningProgressEvent, PlanningSession } from "@/lib/types"

export default function TripPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const [session, setSession] = useState<PlanningSession | null>(null)
  const [progressEvents, setProgressEvents] = useState<PlanningProgressEvent[]>([])
  const [planning, setPlanning] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    let active = true
    async function load() {
      try {
        const current = await getSession(sessionId)
        if (!active) return
        setSession(current)

        if (current.itinerary) {
          return
        }

        setPlanning(true)
        setProgressEvents([])
        const planned = await streamItinerary(sessionId, {
          onProgress: (event) => {
            if (active) setProgressEvents((events) => [...events, event])
          },
        })
        if (active) setSession(planned)
      } catch (loadError) {
        if (active) setError(loadError instanceof Error ? loadError.message : "Planning failed")
      } finally {
        if (active) setPlanning(false)
      }
    }
    void load()
    return () => {
      active = false
    }
  }, [sessionId])

  async function handleStayOverride(stayOptionId: string | null) {
    const updated = await updateStayOverride(sessionId, stayOptionId)
    setSession(updated)
  }

  if (error) return <Centered message={error} />

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-6 text-slate-950 sm:px-6 lg:px-8">
      <div className="mx-auto w-full max-w-7xl space-y-6">
        <PlanningProgress active={planning || !session?.itinerary} events={progressEvents} />
        {session?.itinerary ? (
          <ItineraryView
            session={session}
            onStayOverride={handleStayOverride}
            adjustmentPanel={
              <AdjustmentPanel session={session} onSessionChange={setSession} />
            }
          />
        ) : session ? (
          <div className="grid min-w-0 gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
            <div className="rounded-lg border border-slate-200 bg-white p-6 text-slate-600">
              {canAdjust(session)
                ? "The itinerary is being refreshed. You can still adjust the trip from the side panel."
                : "Generating final itinerary..."}
            </div>
            {canAdjust(session) && (
              <aside className="min-w-0 lg:sticky lg:top-6 lg:max-h-[calc(100vh-3rem)] lg:self-start lg:overflow-y-auto lg:pr-1">
                <AdjustmentPanel session={session} onSessionChange={setSession} />
              </aside>
            )}
          </div>
        ) : (
          <div className="rounded-lg border border-slate-200 bg-white p-6 text-slate-600">
            Generating final itinerary...
          </div>
        )}
      </div>
    </main>
  )
}

function canAdjust(session: PlanningSession): boolean {
  return Boolean(session.stay_recommendation && session.transport_recommendation)
}

function Centered({ message }: { message: string }) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-5 text-slate-700">
      {message}
    </main>
  )
}
