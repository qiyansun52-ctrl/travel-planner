"use client"

import { useState, useCallback } from "react"
import { TravelPlan, ChatMessage } from "@/lib/types"
import { savePlan } from "@/lib/planStore"

export function usePlan(initialPlan: TravelPlan) {
  const [plan, setPlan] = useState<TravelPlan>(initialPlan)
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content: `你的 ${initialPlan.preferences.days} 天${initialPlan.preferences.destination}行程已生成！你可以告诉我任何调整，比如「把第二天改成轻松一点的」或「换一个便宜的住宿」。`,
      timestamp: new Date().toISOString(),
    },
  ])
  const [isGenerating, setIsGenerating] = useState(false)

  const sendAdjustment = useCallback(
    async (userMessage: string) => {
      const userMsg: ChatMessage = {
        role: "user",
        content: userMessage,
        timestamp: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, userMsg])
      setIsGenerating(true)

      try {
        const res = await fetch("/api/plan/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            currentPlan: JSON.stringify(plan.days),
            adjustment: userMessage,
          }),
        })

        if (!res.body) throw new Error("无响应")

        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let raw = ""

        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          raw += decoder.decode(value, { stream: true })
        }

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

        const assistantMsg: ChatMessage = {
          role: "assistant",
          content: "已按你的要求更新行程，右侧已同步刷新。还有什么需要调整的吗？",
          timestamp: new Date().toISOString(),
        }
        setMessages((prev) => [...prev, assistantMsg])
      } catch {
        const errMsg: ChatMessage = {
          role: "assistant",
          content: "调整时出现问题，请再试一次。",
          timestamp: new Date().toISOString(),
        }
        setMessages((prev) => [...prev, errMsg])
      } finally {
        setIsGenerating(false)
      }
    },
    [plan]
  )

  return { plan, messages, isGenerating, sendAdjustment }
}
