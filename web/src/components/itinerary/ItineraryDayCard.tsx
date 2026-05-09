import type { ItineraryDay, ValidatorIssue } from "@/lib/types"
import { ValidatorIssueNote } from "./ValidatorIssueNote"

export function ItineraryDayCard({
  day,
  issues,
}: {
  day: ItineraryDay
  issues: ValidatorIssue[]
}) {
  return (
    <article className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="text-lg font-semibold text-slate-950">
        Day {day.day_index} · {day.date}
      </h3>
      <div className="mt-4 space-y-3">
        {day.segments.map((segment, index) => (
          <div
            key={`${segment.start_time}-${index}`}
            className="grid gap-2 border-l-2 border-slate-200 pl-4 md:grid-cols-[120px_1fr]"
          >
            <div className="text-sm font-medium text-slate-500">
              {segment.start_time}-{segment.end_time}
            </div>
            <div>
              <p className="font-semibold capitalize text-slate-900">
                {segment.type.replaceAll("_", " ")}
              </p>
              <p className="mt-1 text-sm leading-6 text-slate-600">{segment.description}</p>
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
