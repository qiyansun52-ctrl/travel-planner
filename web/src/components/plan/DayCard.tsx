import { DayPlan } from "@/lib/types"
import { ActivityCard } from "./ActivityCard"

interface DayCardProps {
  dayPlan: DayPlan
}

export function DayCard({ dayPlan }: DayCardProps) {
  return (
    <div className="mb-6">
      <div className="flex items-center gap-3 mb-3">
        <span className="bg-blue-600 text-white text-xs font-bold px-3 py-1 rounded-full">
          Day {dayPlan.day}
        </span>
        <span className="font-semibold text-gray-800">{dayPlan.title}</span>
        <span className="ml-auto text-xs text-gray-400">预计 ¥{dayPlan.totalCost}</span>
      </div>
      <div className="flex flex-col gap-2 pl-2 border-l-2 border-blue-100">
        {dayPlan.activities.map((activity) => (
          <ActivityCard key={activity.id} activity={activity} />
        ))}
      </div>
    </div>
  )
}
