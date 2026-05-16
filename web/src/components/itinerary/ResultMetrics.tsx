import type { ResultMetric } from "./resultPageModel"

interface ResultMetricsProps {
  metrics: ResultMetric[]
}

const toneStyles: Record<
  ResultMetric["tone"],
  {
    card: string
    detail: string
    label: string
    status: string
    value: string
  }
> = {
  danger: {
    card: "border-rose-200 bg-rose-50",
    detail: "text-rose-800",
    label: "text-rose-700",
    status: "bg-rose-100 text-rose-800",
    value: "text-rose-950",
  },
  good: {
    card: "border-emerald-200 bg-emerald-50",
    detail: "text-emerald-800",
    label: "text-emerald-700",
    status: "bg-emerald-100 text-emerald-800",
    value: "text-emerald-950",
  },
  neutral: {
    card: "border-slate-200 bg-white",
    detail: "text-slate-600",
    label: "text-slate-500",
    status: "bg-slate-100 text-slate-700",
    value: "text-slate-950",
  },
  warning: {
    card: "border-amber-200 bg-amber-50",
    detail: "text-amber-800",
    label: "text-amber-700",
    status: "bg-amber-100 text-amber-800",
    value: "text-amber-950",
  },
}

export function ResultMetrics({ metrics }: ResultMetricsProps) {
  return (
    <section aria-labelledby="trip-decision-metrics" className="space-y-3">
      <h2
        id="trip-decision-metrics"
        className="text-sm font-semibold uppercase text-slate-500"
      >
        行程判断指标
      </h2>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric) => {
          const styles = toneStyles[metric.tone]

          return (
            <article
              key={`${metric.label}-${metric.status}`}
              className={`min-w-0 rounded-lg border p-4 ${styles.card}`}
            >
              <div className="flex min-w-0 flex-col gap-2">
                <p
                  className={`break-words text-xs font-semibold uppercase ${styles.label}`}
                >
                  {metric.label}
                </p>
                <p
                  className={`w-fit max-w-full rounded px-2 py-1 text-xs font-semibold leading-5 ${styles.status}`}
                >
                  {metric.status}
                </p>
              </div>
              <p className={`mt-4 break-words text-2xl font-semibold ${styles.value}`}>
                {metric.value}
              </p>
              <p className={`mt-2 text-sm leading-5 ${styles.detail}`}>{metric.detail}</p>
            </article>
          )
        })}
      </div>
    </section>
  )
}
