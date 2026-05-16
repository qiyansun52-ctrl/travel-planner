import type { ItineraryDay, ValidatorIssue } from "@/lib/types"
import { formatBand } from "./resultPageModel"
import { ValidatorIssueNote } from "./ValidatorIssueNote"

export function ItineraryDayCard({
  day,
  issues,
}: {
  day: ItineraryDay
  issues: ValidatorIssue[]
}) {
  const firstNote = day.notes.find((note) => note.trim().length > 0)

  return (
    <article className="min-w-0 rounded-lg border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
      <header className="min-w-0 border-b border-slate-200 pb-4">
        <p className="text-sm font-medium text-slate-500">第 {day.day_index} 天</p>
        <h3 className="mt-1 break-words text-xl font-semibold text-slate-950">
          <time dateTime={day.date}>{formatDisplayDate(day.date)}</time>
        </h3>
        {firstNote && (
          <p className="mt-3 break-words text-sm leading-6 text-slate-600">{firstNote}</p>
        )}
      </header>

      <div className="mt-4 space-y-3">
        {day.segments.map((segment, index) => (
          <div
            key={`${segment.start_time}-${index}`}
            className="grid min-w-0 gap-3 rounded-md border border-slate-200 bg-slate-50 px-3 py-3 sm:grid-cols-[104px_minmax(0,1fr)] sm:px-4"
          >
            <div className="min-w-0 text-sm font-semibold text-slate-500">
              <span className="whitespace-nowrap">
                {segment.start_time}-{segment.end_time}
              </span>
            </div>
            <div className="min-w-0">
              <div className="flex min-w-0 flex-wrap items-start gap-2">
                <span className="max-w-full break-words rounded-md bg-white px-2 py-1 text-xs font-semibold text-slate-600 ring-1 ring-slate-200">
                  {formatSegmentType(segment.type)}
                </span>
                {segment.cost_estimate && (
                  <span className="max-w-full break-words rounded-md bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-800 ring-1 ring-emerald-100">
                    {formatBand(segment.cost_estimate)}
                  </span>
                )}
              </div>

              <p className="mt-2 break-words text-base font-semibold leading-6 text-slate-950">
                {segment.place?.name ?? segment.description}
              </p>
              {segment.place?.name && (
                <p className="mt-1 break-words text-sm leading-6 text-slate-600">
                  {segment.description}
                </p>
              )}
              {segment.place?.address && (
                <p className="mt-2 break-words text-sm leading-5 text-slate-500">
                  {segment.place.address}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
      {issues.length > 0 && (
        <div className="mt-4 space-y-2">
          {issues.map((issue) => (
            <ValidatorIssueNote key={`${issue.code}-${issue.message}`} issue={issue} />
          ))}
        </div>
      )}
    </article>
  )
}

function formatSegmentType(type: ItineraryDay["segments"][number]["type"]): string {
  const labels: Record<ItineraryDay["segments"][number]["type"], string> = {
    attraction: "体验",
    food: "餐饮",
    hotel_checkin: "入住",
    hotel_checkout: "退房",
    hotel_return: "返回住宿",
    rest: "休息",
    transit: "移动",
  }
  return labels[type]
}

function formatDisplayDate(value: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (!match) {
    return value
  }

  const [, year, month, day] = match
  const date = new Date(Date.UTC(Number(year), Number(month) - 1, Number(day)))

  return new Intl.DateTimeFormat("zh-CN", {
    day: "numeric",
    month: "short",
    timeZone: "UTC",
    weekday: "short",
    year: "numeric",
  }).format(date)
}
