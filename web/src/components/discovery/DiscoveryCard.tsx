"use client"

import { DiscoveryCard as DiscoveryCardType } from "@/domain/schemas"

interface DiscoveryCardProps {
  card: DiscoveryCardType
  selected: boolean
  onToggle: (id: string) => void
}

export function DiscoveryCard({ card, selected, onToggle }: DiscoveryCardProps) {
  const statusLabel =
    card.enrichment_status === "complete"
      ? "Complete"
      : card.enrichment_status === "partial"
        ? "Partial"
        : "Text only"

  return (
    <article className="flex min-h-64 flex-col overflow-hidden rounded-lg border border-slate-200 bg-white">
      {card.enrichment_status !== "minimal" && (
        <div className="h-28 bg-slate-100">
          {card.image_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={card.image_url} alt="" className="h-full w-full object-cover" />
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-slate-500">
              Image pending
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
        <div className="flex flex-wrap gap-2">
          {card.tags.map((tag) => (
            <span key={tag} className="rounded bg-sky-50 px-2 py-1 text-xs text-sky-800">
              {tag}
            </span>
          ))}
        </div>
        <div className="mt-auto flex items-center justify-between gap-3">
          <span className="text-sm font-medium capitalize text-slate-700">
            {card.cost_signal}
          </span>
          <button
            type="button"
            aria-label={`${selected ? "Unselect" : "Select"} ${card.name}`}
            onClick={() => onToggle(card.id)}
            className={`h-9 rounded-md px-3 text-sm font-semibold ${
              selected
                ? "bg-slate-950 text-white hover:bg-slate-800"
                : "border border-slate-300 bg-white text-slate-800 hover:bg-slate-50"
            }`}
          >
            {selected ? "Selected" : "Select"}
          </button>
        </div>
      </div>
    </article>
  )
}
