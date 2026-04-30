import { Activity } from "@/lib/types"

const typeColors: Record<Activity["type"], string> = {
  attraction: "bg-blue-100 text-blue-700",
  food: "bg-orange-100 text-orange-700",
  transport: "bg-green-100 text-green-700",
  hotel: "bg-purple-100 text-purple-700",
  free: "bg-gray-100 text-gray-600",
}

const typeLabels: Record<Activity["type"], string> = {
  attraction: "景点",
  food: "餐饮",
  transport: "交通",
  hotel: "住宿",
  free: "自由",
}

interface ActivityCardProps {
  activity: Activity
}

export function ActivityCard({ activity }: ActivityCardProps) {
  return (
    <div className="flex gap-3 p-3 rounded-lg bg-white border border-gray-100 hover:border-gray-200 transition-colors">
      <div className="flex flex-col items-center gap-1 min-w-[48px]">
        <span className="text-xs font-medium text-gray-500">{activity.time}</span>
        {activity.endTime && (
          <span className="text-xs text-gray-300">{activity.endTime}</span>
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${typeColors[activity.type]}`}>
            {typeLabels[activity.type]}
          </span>
          {activity.estimatedCost !== undefined && (
            <span className="text-xs text-gray-400">¥{activity.estimatedCost}</span>
          )}
        </div>
        <p className="font-medium text-gray-900 text-sm">{activity.place}</p>
        <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">{activity.description}</p>
        {activity.tips && (
          <p className="text-xs text-amber-600 mt-1 bg-amber-50 px-2 py-1 rounded">
            💡 {activity.tips}
          </p>
        )}
      </div>
    </div>
  )
}
