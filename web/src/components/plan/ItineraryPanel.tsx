import { TravelPlan } from "@/lib/types"
import { DayCard } from "./DayCard"

interface ItineraryPanelProps {
  plan: TravelPlan
}

export function ItineraryPanel({ plan }: ItineraryPanelProps) {
  const { preferences, days, budget, tips } = plan

  return (
    <div className="flex flex-col gap-4 h-full overflow-y-auto p-6">
      <div className="bg-gradient-to-r from-blue-600 to-blue-400 rounded-xl p-5 text-white">
        <p className="text-xs opacity-75 mb-1">{preferences.departureCity} → {preferences.destination}</p>
        <h2 className="text-xl font-bold">{preferences.destination} · {preferences.days}日游</h2>
        <p className="text-sm opacity-80 mt-1">{preferences.departureDate} 出发 · 预算 ¥{preferences.totalBudget}</p>
      </div>

      {days.map((day) => (
        <DayCard key={day.day} dayPlan={day} />
      ))}

      <div className="mt-2 p-4 bg-amber-50 rounded-xl border border-amber-100">
        <h3 className="font-semibold text-gray-800 mb-2 text-sm">实用提示</h3>
        <ul className="flex flex-col gap-1">
          {tips.map((tip, i) => (
            <li key={i} className="text-xs text-gray-600 flex gap-2">
              <span className="text-amber-500 flex-shrink-0">•</span>
              {tip}
            </li>
          ))}
        </ul>
      </div>

      <div className="p-4 bg-gray-50 rounded-xl border border-gray-100">
        <h3 className="font-semibold text-gray-800 mb-3 text-sm">费用预算</h3>
        {Object.entries({
          交通: budget.transport,
          住宿: budget.accommodation,
          餐饮: budget.food,
          景点: budget.attractions,
          其他: budget.other,
        }).map(([label, amount]) => (
          <div key={label} className="flex justify-between text-xs text-gray-600 mb-1">
            <span>{label}</span>
            <span>¥{amount}</span>
          </div>
        ))}
        <div className="flex justify-between text-sm font-bold text-gray-900 mt-2 pt-2 border-t border-gray-200">
          <span>合计</span>
          <span>¥{budget.total}</span>
        </div>
      </div>
    </div>
  )
}
