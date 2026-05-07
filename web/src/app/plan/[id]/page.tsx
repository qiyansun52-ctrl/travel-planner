"use client"

/* eslint-disable react-hooks/set-state-in-effect */

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { TravelPlan } from "@/lib/types"
import { getPlan } from "@/lib/planStore"
import { usePlan } from "@/hooks/usePlan"
import { ItineraryPanel } from "@/components/plan/ItineraryPanel"
import { AIChatPanel } from "@/components/plan/AIChatPanel"

export default function PlanPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const [initialPlan, setInitialPlan] = useState<TravelPlan | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const plan = getPlan(id)
    if (!plan) {
      router.push("/")
      return
    }
    setInitialPlan(plan)
    setLoading(false)
  }, [id, router])

  if (loading || !initialPlan) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-400">
        加载中…
      </div>
    )
  }

  return <PlanView initialPlan={initialPlan} />
}

function PlanView({ initialPlan }: { initialPlan: TravelPlan }) {
  const { plan, messages, isGenerating, sendAdjustment } = usePlan(initialPlan)

  return (
    <div className="h-screen flex overflow-hidden">
      <div className="w-80 flex-shrink-0 flex flex-col overflow-hidden">
        <AIChatPanel messages={messages} isGenerating={isGenerating} onSend={sendAdjustment} />
      </div>
      <div className="flex-1 overflow-hidden">
        <ItineraryPanel plan={plan} />
      </div>
    </div>
  )
}
