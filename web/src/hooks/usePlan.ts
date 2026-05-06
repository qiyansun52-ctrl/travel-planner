"use client"

import { useState, useCallback } from "react"
import { TravelPlan, ChatMessage } from "@/lib/types"
import { savePlan } from "@/lib/planStore"

export function usePlan(initialPlan: TravelPlan) {
  const [plan, setPlan] = useState<TravelPlan>(initialPlan)
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    const sel = initialPlan.selectedAttractions
    const selText =
      sel.length > 0
        ? `已将你选择的${sel.map((c) => c.name).join("、")}安排进行程。`
        : ""
    return [
      {
        role: "assistant",
        content: `你的 ${initialPlan.preferences.days} 天${initialPlan.preferences.destination}行程已生成！${selText}你可以告诉我任何调整，比如「把第二天改成轻松一点的」或「把交通方案换成飞机」。`,
        timestamp: new Date().toISOString(),
      },
    ]
  })
  const [isGenerating, setIsGenerating] = useState(false)

  const sendAdjustment = useCallback(
    async (userMessage: string) => {
      setMessages((prev) => [
        ...prev,
        { role: "user", content: userMessage, timestamp: new Date().toISOString() },
      ])
      setIsGenerating(true)

      try {
        const res = await fetch("/api/plan/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            currentPlan: JSON.stringify(plan.days),
            adjustment: userMessage,
            selectedAttractions: plan.selectedAttractions,
          }),
        })

        if (!res.ok) throw new Error("调整失败")
        const raw = await res.text()
        const jsonMatch = raw.match(/\{[\s\S]*\}/)
        if (!jsonMatch) throw new Error("无法解析调整结果")

        const updated = JSON.parse(jsonMatch[0])
        const newPlan: TravelPlan = {
          ...plan,
          days: updated.days ?? plan.days,
          budget: updated.budget ?? plan.budget,
          tips: updated.tips ?? plan.tips,
        }
        setPlan(newPlan)
        savePlan(newPlan)

        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: "已按你的要求更新行程，右侧已同步刷新。还有什么需要调整的吗？",
            timestamp: new Date().toISOString(),
          },
        ])
      } catch {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: "调整时出现问题，请再试一次。",
            timestamp: new Date().toISOString(),
          },
        ])
      } finally {
        setIsGenerating(false)
      }
    },
    [plan]
  )

  return { plan, messages, isGenerating, sendAdjustment }
}
