"use client"

import { useState, FormEvent } from "react"
import { useRouter } from "next/navigation"
import { UserPreferences, TravelPlan } from "@/lib/types"
import { savePlan } from "@/lib/planStore"
import { Button } from "@/components/ui/Button"
import { TextArea } from "@/components/ui/TextArea"
import { nanoid } from "nanoid"

export function SearchForm() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState<UserPreferences>({
    destination: "",
    departureCity: "",
    departureDate: "",
    days: 3,
    totalBudget: 5000,
    accommodationDescription: "",
    experienceDescription: "",
  })

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setLoading(true)

    try {
      const res = await fetch("/api/plan/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ preferences: form }),
      })

      if (!res.ok) throw new Error("生成失败，请重试")
      if (!res.body) throw new Error("无响应数据")

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let raw = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        raw += decoder.decode(value, { stream: true })
      }

      const jsonMatch = raw.match(/\{[\s\S]*\}/)
      if (!jsonMatch) throw new Error("无法解析行程数据")

      const planData = JSON.parse(jsonMatch[0])
      const plan: TravelPlan = {
        id: nanoid(),
        preferences: form,
        days: planData.days,
        budget: planData.budget,
        tips: planData.tips,
        createdAt: new Date().toISOString(),
      }

      savePlan(plan)
      router.push(`/plan/${plan.id}`)
    } catch (err) {
      alert(err instanceof Error ? err.message : "发生错误，请重试")
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-6 w-full max-w-xl">
      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">目的地</label>
          <input
            required
            type="text"
            placeholder="例：上海、京都、巴黎"
            className="rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
            value={form.destination}
            onChange={(e) => setForm({ ...form, destination: e.target.value })}
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">出发城市</label>
          <input
            required
            type="text"
            placeholder="例：北京"
            className="rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
            value={form.departureCity}
            onChange={(e) => setForm({ ...form, departureCity: e.target.value })}
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">出发日期</label>
          <input
            required
            type="date"
            className="rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
            value={form.departureDate}
            onChange={(e) => setForm({ ...form, departureDate: e.target.value })}
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">旅行天数</label>
          <input
            required
            type="number"
            min={1}
            max={30}
            className="rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
            value={form.days}
            onChange={(e) => setForm({ ...form, days: Number(e.target.value) })}
          />
        </div>
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-700">总预算</label>
        <div className="relative">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">¥</span>
          <input
            required
            type="number"
            min={100}
            placeholder="5000"
            className="w-full rounded-lg border border-gray-200 pl-7 pr-3 py-2 text-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
            value={form.totalBudget || ""}
            onChange={(e) => setForm({ ...form, totalBudget: Number(e.target.value) })}
          />
        </div>
        <p className="text-xs text-gray-400">含交通、住宿、餐饮、景点</p>
      </div>

      <TextArea
        label="你对住宿有什么期待？"
        hint="用你自己的话描述，不必选择类别"
        placeholder="例：想住在森林里的小木屋，最好有壁炉，能听到虫鸣声…"
        rows={3}
        required
        value={form.accommodationDescription}
        onChange={(e) => setForm({ ...form, accommodationDescription: e.target.value })}
      />

      <TextArea
        label="这次旅行你最想体验什么？"
        hint="可以包括想去的地方、想做的事、想要的感觉"
        placeholder="例：想去当地人才知道的小馆子，不想跟团，希望有一个下午什么都不做，就坐在海边发呆…"
        rows={4}
        required
        value={form.experienceDescription}
        onChange={(e) => setForm({ ...form, experienceDescription: e.target.value })}
      />

      <Button type="submit" disabled={loading} className="w-full py-3 text-base">
        {loading ? "AI 正在规划中…" : "让 AI 帮我规划 →"}
      </Button>
    </form>
  )
}
