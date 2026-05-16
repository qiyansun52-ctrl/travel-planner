"use client"

import type { DiscoveryCard as DiscoveryCardType } from "@/lib/types"

interface DiscoveryCardProps {
  card: DiscoveryCardType
  selected: boolean
  onToggle: (id: string) => void
}

export function DiscoveryCard({ card, selected, onToggle }: DiscoveryCardProps) {
  const statusLabel =
    card.enrichment_status === "complete"
      ? "已验证"
      : card.enrichment_status === "partial"
        ? "部分验证"
        : "文本线索"

  return (
    <article className="flex min-h-64 flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      {card.enrichment_status !== "minimal" && (
        <div className="h-28 bg-slate-100">
          {card.image_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={card.image_url} alt="" className="h-full w-full object-cover" />
          ) : (
            <div className="flex h-full items-center justify-center bg-teal-50 px-4 text-center text-sm font-medium text-teal-900">
              图片待补充 · {card.category}
            </div>
          )}
        </div>
      )}
      <div className="flex flex-1 flex-col gap-3 p-4">
        <div className="flex items-start justify-between gap-3">
          <h3 className="text-lg font-semibold leading-snug text-slate-950">{card.name}</h3>
          <span className="rounded bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600">
            {statusLabel}
          </span>
        </div>
        <p className="text-sm leading-6 text-slate-600">{card.reason}</p>
        {card.reservation_hint && (
          <p className="rounded-md bg-amber-50 px-3 py-2 text-sm leading-5 text-amber-800">
            {card.reservation_hint}
          </p>
        )}
        <div className="flex flex-wrap gap-2">
          {card.tags.map((tag) => (
            <span key={tag} className="rounded bg-sky-50 px-2 py-1 text-xs text-sky-800">
              {tag}
            </span>
          ))}
        </div>
        <div className="mt-auto flex items-center justify-between gap-3">
          <span className="text-sm font-medium capitalize text-slate-700">
            {formatCostSignal(card.cost_signal)}
          </span>
          <button
            type="button"
            aria-label={`${selected ? "取消选择" : "选择"} ${card.name}`}
            onClick={() => onToggle(card.id)}
            className={`h-9 rounded-md px-3 text-sm font-semibold ${
              selected
                ? "bg-slate-950 text-white hover:bg-slate-800"
                : "border border-slate-300 bg-white text-slate-800 hover:bg-slate-50"
            }`}
          >
            {selected ? "已选择" : "选择"}
          </button>
        </div>
      </div>
    </article>
  )
}

function formatCostSignal(value: string): string {
  const labels: Record<string, string> = {
    free: "免费",
    low: "低预算",
    medium: "中等预算",
    high: "较高预算",
    unknown: "待确认",
  }
  return labels[value] ?? value
}
