"use client"

import { useEffect, useState } from "react"
import { useParams } from "next/navigation"
import { AdjustmentPanel } from "@/components/chat/AdjustmentPanel"
import { ItineraryView } from "@/components/itinerary/ItineraryView"
import { PlanningProgress } from "@/components/itinerary/PlanningProgress"
import { ToastContainer } from "@/components/ui/Toast"
import { useToast } from "@/components/ui/useToast"
import { getSession, streamItinerary, updateStayOverride } from "@/lib/apiClient"
import type { PlanningProgressEvent, PlanningSession } from "@/lib/types"

export default function TripPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const [session, setSession] = useState<PlanningSession | null>(null)
  const [progressEvents, setProgressEvents] = useState<PlanningProgressEvent[]>([])
  const [planning, setPlanning] = useState(false)
  const [error, setError] = useState("")
  const [retryKey, setRetryKey] = useState(0)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const { toasts, toast, dismiss } = useToast()

  useEffect(() => {
    let active = true

    async function load() {
      setError("")
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
        if (active) {
          setError(loadError instanceof Error ? loadError.message : "规划失败")
          toast("规划出错，请重试", "error")
        }
      } finally {
        if (active) setPlanning(false)
      }
    }
    void load()
    return () => {
      active = false
    }
  }, [retryKey, sessionId, toast])

  async function handleStayOverride(stayOptionId: string | null) {
    const updated = await updateStayOverride(sessionId, stayOptionId)
    setSession(updated)
  }

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-6 text-slate-950 sm:px-6 lg:px-8">
      <div className="mx-auto w-full max-w-7xl space-y-6">
        <PlanningProgress
          active={!error && (planning || !session?.itinerary)}
          events={progressEvents}
        />

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-5 py-4 text-red-800">
            <p className="font-semibold">规划出错</p>
            <p className="mt-1 text-sm">{error}</p>
            <button
              type="button"
              onClick={() => setRetryKey((key) => key + 1)}
              className="mt-3 rounded-md border border-red-300 bg-white px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-50"
            >
              重试
            </button>
          </div>
        )}

        {!error && session?.itinerary ? (
          <ItineraryView
            session={session}
            onStayOverride={handleStayOverride}
            adjustmentPanel={
              <AdjustmentPanel session={session} onSessionChange={setSession} />
            }
          />
        ) : !error && session ? (
          <div className="grid min-w-0 gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
            <div className="rounded-lg border border-slate-200 bg-white p-6 text-slate-600">
              {canAdjust(session)
                ? "行程正在刷新，你仍然可以从侧边调整区继续提出需求。"
                : "正在生成完整行程..."}
            </div>
            {canAdjust(session) && (
              <aside className="min-w-0 lg:sticky lg:top-6 lg:max-h-[calc(100vh-3rem)] lg:self-start lg:overflow-y-auto lg:pr-1">
                <AdjustmentPanel session={session} onSessionChange={setSession} />
              </aside>
            )}
          </div>
        ) : !error ? (
          <div className="rounded-lg border border-slate-200 bg-white p-6 text-slate-600">
            正在生成完整行程...
          </div>
        ) : null}
      </div>

      {session?.itinerary && (
        <div className="fixed bottom-5 right-5 z-40 lg:hidden">
          <button
            type="button"
            onClick={() => setDrawerOpen(true)}
            className="flex h-14 w-14 items-center justify-center rounded-full bg-teal-600 text-white shadow-lg hover:bg-teal-700"
            aria-label="打开调整面板"
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path
                d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"
                stroke="currentColor"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
              />
            </svg>
          </button>
        </div>
      )}

      {drawerOpen && session?.itinerary && (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-label="调整行程">
          <div
            className="absolute inset-0 bg-slate-950/50"
            onClick={() => setDrawerOpen(false)}
            aria-hidden="true"
          />
          <div className="absolute bottom-0 left-0 right-0 max-h-[80vh] overflow-y-auto rounded-t-2xl bg-white pb-6">
            <div className="sticky top-0 flex items-center justify-between border-b border-slate-100 bg-white px-4 py-3">
              <span className="text-sm font-semibold text-slate-950">调整行程</span>
              <button
                type="button"
                onClick={() => setDrawerOpen(false)}
                className="rounded-md p-1 text-slate-500 hover:text-slate-700"
                aria-label="关闭"
              >
                ✕
              </button>
            </div>
            <div className="p-4">
              <AdjustmentPanel session={session} onSessionChange={setSession} />
            </div>
          </div>
        </div>
      )}

      <ToastContainer toasts={toasts} onDismiss={dismiss} />
    </main>
  )
}

function canAdjust(session: PlanningSession): boolean {
  return Boolean(session.stay_recommendation && session.transport_recommendation)
}
