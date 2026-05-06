"use client"

import { useState, FormEvent } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/Button"

export function SearchForm() {
  const router = useRouter()
  const [destination, setDestination] = useState("")
  const [budget, setBudget] = useState(5000)

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    router.push(`/discover/${encodeURIComponent(destination)}?budget=${budget}`)
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5 w-full max-w-md">
      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-700">你想去哪里？</label>
        <input
          required
          autoFocus
          type="text"
          placeholder="例：上海、京都、巴黎"
          className="rounded-xl border border-gray-200 px-4 py-3 text-base focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
          value={destination}
          onChange={(e) => setDestination(e.target.value)}
        />
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-700">预算大概多少？</label>
        <div className="relative">
          <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400">¥</span>
          <input
            required
            type="number"
            min={100}
            placeholder="5000"
            className="w-full rounded-xl border border-gray-200 pl-8 pr-4 py-3 text-base focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
            value={budget || ""}
            onChange={(e) => setBudget(Number(e.target.value))}
          />
        </div>
        <p className="text-xs text-gray-400">含交通、住宿、餐饮、景点</p>
      </div>

      <Button type="submit" className="w-full py-3 text-base">
        探索目的地 →
      </Button>
    </form>
  )
}
