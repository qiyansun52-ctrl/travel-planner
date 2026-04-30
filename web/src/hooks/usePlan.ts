"use client"

import Anthropic from "@anthropic-ai/sdk"
import { useState, useCallback } from "react"
import { TravelPlan, ChatMessage } from "@/lib/types"
import { buildAdjustmentPrompt } from "@/lib/claude"
import { savePlan } from "@/lib/planStore"

const client = new Anthropic({
  authToken: process.env.NEXT_PUBLIC_ANTHROPIC_API_KEY,
  baseURL: process.env.NEXT_PUBLIC_ANTHROPIC_BASE_URL,
  dangerouslyAllowBrowser: true,
})

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
        const prompt = buildAdjustmentPrompt(JSON.stringify(plan.days), userMessage)
        const response = await client.messages.create({
          model: "claude-sonnet-4-6",
          max_tokens: 4096,
          messages: [{ role: "user", content: prompt }],
        })

        const raw = response.content[0].type === "text" ? response.content[0].text : ""
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
