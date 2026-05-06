"use client"

import { useEffect, useState, useMemo } from "react"
import { useParams, useRouter, useSearchParams } from "next/navigation"
import {
  AttractionCard as AttractionCardType,
  DiscoverSections,
  TravelPlan,
  UserPreferences,
} from "@/lib/types"
import { SectionBlock } from "@/components/discover/SectionBlock"
import { SelectionBar } from "@/components/discover/SelectionBar"
import { savePlan } from "@/lib/planStore"
import { nanoid } from "nanoid"

const LOADING_STEPS = [
  "正在搜索旅游攻略…",
  "收集交通与景点信息…",
  "收集美食与体验信息…",
  "AI 正在整理卡片…",
]

const EMPTY_SECTIONS: DiscoverSections = {
  experience: [],
  transport: [],
  food: [],
}

export default function DiscoverPage() {
  const params = useParams<{ destination: string }>()
  const searchParams = useSearchParams()
  const router = useRouter()

  const destination = decodeURIComponent(params.destination)
  const budget = Number(searchParams.get("budget") ?? 5000)

  const [sections, setSections] = useState<DiscoverSections>(EMPTY_SECTIONS)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [loadingStep, setLoadingStep] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [generating, setGenerating] = useState(false)

  useEffect(() => {
    const cacheKey = `discover_${destination}`
    const cached = sessionStorage.getItem(cacheKey)
    if (cached) {
      setSections(JSON.parse(cached))
      setLoading(false)
      return
    }

    const interval = setInterval(() => {
      setLoadingStep((prev) => Math.min(prev + 1, LOADING_STEPS.length - 1))
    }, 2000)

    fetch(`/api/discover?destination=${encodeURIComponent(destination)}`)
      .then((res) => {
        if (!res.ok) throw new Error("搜索失败，请返回重试")
        return res.json()
      })
      .then((data: { sections: DiscoverSections }) => {
        setSections(data.sections)
        sessionStorage.setItem(cacheKey, JSON.stringify(data.sections))
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => {
        clearInterval(interval)
        setLoading(false)
      })

    return () => clearInterval(interval)
  }, [destination])

  const allCards = useMemo(
    () => [...sections.experience, ...sections.transport, ...sections.food],
    [sections]
  )

  const selectedCards = useMemo(
    () => allCards.filter((c) => selected.has(c.id)),
    [allCards, selected]
  )

  function toggleCard(id: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  async function handleGenerate(prefs: UserPreferences) {
    setGenerating(true)
    try {
      const res = await fetch("/api/plan/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ preferences: prefs, selectedAttractions: selectedCards }),
      })
      if (!res.ok) throw new Error("生成失败，请重试")
      const raw = await res.text()
      const jsonMatch = raw.match(/\{[\s\S]*\}/)
      if (!jsonMatch) throw new Error("无法解析行程数据")
      const planData = JSON.parse(jsonMatch[0])
      const plan: TravelPlan = {
        id: nanoid(),
        preferences: prefs,
        selectedAttractions: selectedCards,
        days: planData.days,
        budget: planData.budget,
        tips: planData.tips,
        createdAt: new Date().toISOString(),
      }
      savePlan(plan)
      router.push(`/plan/${plan.id}`)
    } catch (err) {
      alert(err instanceof Error ? err.message : "发生错误，请重试")
      setGenerating(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-gradient-to-br from-blue-50 to-slate-50">
        <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-gray-700 text-lg font-medium">{LOADING_STEPS[loadingStep]}</p>
        <p className="text-gray-400 text-sm">正在搜索 {destination} 的旅游信息</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4">
        <p className="text-red-500">{error}</p>
        <button onClick={() => router.push("/")} className="text-blue-600 underline">
          返回首页
        </button>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-32">
      <div className="bg-white border-b border-gray-100 px-4 py-4 sticky top-0 z-40 shadow-sm">
        <div className="max-w-5xl mx-auto flex items-center gap-3">
          <button
            onClick={() => router.push("/")}
            className="text-gray-400 hover:text-gray-600 text-xl"
          >
            ←
          </button>
          <div>
            <h1 className="font-bold text-gray-900 text-xl">{destination}</h1>
            <p className="text-xs text-gray-400">
              选择感兴趣的内容，AI 将为你量身制定行程
            </p>
          </div>
          {selected.size > 0 && (
            <span className="ml-auto bg-blue-500 text-white text-xs font-bold px-3 py-1 rounded-full">
              已选 {selected.size}
            </span>
          )}
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 pt-8 flex flex-col gap-12">
        <SectionBlock
          section="experience"
          cards={sections.experience}
          selected={selected}
          onToggle={toggleCard}
        />
        <SectionBlock
          section="transport"
          cards={sections.transport}
          selected={selected}
          onToggle={toggleCard}
        />
        <SectionBlock
          section="food"
          cards={sections.food}
          selected={selected}
          onToggle={toggleCard}
        />
      </div>

      <SelectionBar
        selected={selectedCards}
        destination={destination}
        budget={budget}
        onGenerate={handleGenerate}
        generating={generating}
      />
    </div>
  )
}
