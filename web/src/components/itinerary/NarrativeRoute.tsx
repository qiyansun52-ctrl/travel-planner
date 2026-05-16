import type { NarrativeRouteItem } from "./resultPageModel"

interface NarrativeRouteProps {
  items: NarrativeRouteItem[]
}

export function NarrativeRoute({ items }: NarrativeRouteProps) {
  if (items.length === 0) {
    return null
  }

  return (
    <section
      aria-labelledby="narrative-route-title"
      className="rounded-lg border border-slate-200 bg-white p-4 sm:p-5"
    >
      <div className="min-w-0">
        <p className="text-sm font-semibold uppercase text-teal-700">
          叙事路线
        </p>
        <h2
          id="narrative-route-title"
          className="mt-2 break-words text-xl font-semibold text-slate-950"
        >
          行程弧线
        </h2>
      </div>

      <ol className="mt-5 space-y-4">
        {items.map((item) => (
          <li
            key={`${item.dayIndex}-${item.date}`}
            className="grid min-w-0 gap-3 border-l-2 border-slate-200 pl-4 sm:grid-cols-[112px_1fr]"
          >
            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase text-slate-500">
                第 {item.dayIndex} 天
              </p>
              <p className="mt-1 break-words text-sm font-medium text-slate-700">
                {formatDate(item.date)}
              </p>
            </div>

            <article className="min-w-0">
              <h3 className="break-words text-base font-semibold text-slate-950">
                {item.title}
              </h3>
              {item.note && (
                <p className="mt-2 break-words text-sm leading-6 text-slate-600">
                  {item.note}
                </p>
              )}
              <p className="mt-2 break-words text-sm font-medium text-slate-700">
                {item.budgetHint}
              </p>
              {item.anchors.length > 0 && (
                <div className="mt-3 flex min-w-0 flex-wrap gap-2">
                  {item.anchors.map((anchor, index) => (
                    <span
                      key={`${item.dayIndex}-${anchor}-${index}`}
                      title={anchor}
                      className="max-w-full truncate rounded-md bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700"
                    >
                      {anchor}
                    </span>
                  ))}
                </div>
              )}
            </article>
          </li>
        ))}
      </ol>
    </section>
  )
}

function formatDate(value: string): string {
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
    year: "numeric",
  }).format(date)
}
