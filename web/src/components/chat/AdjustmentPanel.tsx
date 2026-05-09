"use client"

import { FormEvent, useState } from "react"
import { PlanningSession } from "@/domain/schemas"
import { submitAdjustment, type AdjustmentResponse } from "@/lib/apiClient"
import { TypeCConfirmationCard } from "./TypeCConfirmationCard"

interface AdjustmentPanelProps {
  session: PlanningSession
  onSessionChange: (session: PlanningSession) => void
}

export function AdjustmentPanel({ session, onSessionChange }: AdjustmentPanelProps) {
  const [message, setMessage] = useState("")
  const [status, setStatus] = useState("")
  const [pendingConfirmation, setPendingConfirmation] = useState<AdjustmentResponse | null>(null)

  async function send(action?: "replan" | "save_and_start_new" | "cancel") {
    const response = await submitAdjustment({
      sessionId: session.session_id,
      message,
      typeCAction: action,
    })
    onSessionChange(response.session)
    setStatus(response.message)
    setPendingConfirmation(response.confirmation ? response : null)
    if (!response.confirmation) setMessage("")
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!message.trim()) return
    await send()
  }

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="text-lg font-semibold text-slate-950">Adjust itinerary</h2>
      <form onSubmit={handleSubmit} className="mt-3 space-y-3">
        <label className="flex flex-col gap-2 text-sm font-medium text-slate-700">
          Adjustment request
          <textarea
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            className="min-h-24 rounded-md border border-slate-300 px-3 py-2 text-base text-slate-950 outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
          />
        </label>
        <button
          type="submit"
          className="h-10 rounded-md bg-slate-950 px-4 text-sm font-semibold text-white hover:bg-slate-800"
        >
          Send adjustment
        </button>
      </form>
      {status && <p className="mt-3 text-sm font-medium text-slate-700">{status}</p>}
      {pendingConfirmation?.confirmation && (
        <div className="mt-3">
          <TypeCConfirmationCard
            confirmation={pendingConfirmation.confirmation}
            onAction={(action) => void send(action)}
          />
        </div>
      )}
    </section>
  )
}
