"use client"

import type { DiscoveryCard as DiscoveryCardType } from "@/lib/types"

const CATEGORY_COLORS: Record<string, string> = {
  attraction: "bg-violet-50 text-violet-700",
  food: "bg-amber-50 text-amber-700",
  neighborhood: "bg-teal-50 text-teal-700",
  activity: "bg-blue-50 text-blue-700",
  accommodation: "bg-rose-50 text-rose-700",
}

const CATEGORY_LABELS: Record<string, string> = {
  attraction: "景点",
  food: "餐饮",
  neighborhood: "街区",
  activity: "活动",
  accommodation: "住宿",
}

const COST_DOTS: Record<string, string> = {
  free: "免费",
  low: "·",
  medium: "··",
  high: "···",
}

interface DiscoveryCardProps {
  card: DiscoveryCardType
  selected: boolean
  onToggle: (id: string) => void
}

export function DiscoveryCard({ card, selected, onToggle }: DiscoveryCardProps) {
  const categoryColor = CATEGORY_COLORS[card.category] ?? "bg-slate-50 text-slate-700"
  const categoryLabel = CATEGORY_LABELS[card.category] ?? card.category
  const costDots = COST_DOTS[card.cost_signal] ?? card.cost_signal

  return (
    <article
      className={`
        group relative flex min-h-64 flex-col overflow-hidden rounded-[var(--radius-card)] border bg-white
        shadow-[var(--shadow-card)] transition-[box-shadow,border-color] duration-[var(--transition-base)]
        ${
          selected
            ? "border-teal-500 shadow-[0_0_0_2px_theme(colors.teal.500)]"
            : "border-slate-200 hover:shadow-[var(--shadow-card-hover)]"
        }
      `}
    >
      <div className="relative aspect-video overflow-hidden bg-slate-100">
        {card.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={card.image_url}
            alt=""
            className="h-full w-full object-cover transition-transform duration-[var(--transition-slow)] group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full items-center justify-center bg-gradient-to-br from-slate-100 to-slate-200">
            <span className="text-3xl">{getCategoryEmoji(card.category)}</span>
          </div>
        )}

        <span
          className={`absolute left-3 top-3 rounded-[var(--radius-badge)] px-2 py-0.5 text-xs font-semibold ${categoryColor}`}
        >
          {categoryLabel}
        </span>

        {selected && (
          <span
            aria-label="已选择"
            className="absolute right-3 top-3 flex h-6 w-6 items-center justify-center rounded-full bg-teal-500 text-white shadow-sm"
          >
            <CheckIcon />
          </span>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-3 p-4">
        <h3 className="break-words text-base font-semibold leading-snug text-slate-950">
          {card.name}
        </h3>
        <p className="line-clamp-3 text-sm leading-6 text-slate-600">{card.reason}</p>

        {card.reservation_hint && (
          <p className="rounded-md bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-800">
            {card.reservation_hint}
          </p>
        )}

        {card.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {card.tags.slice(0, 4).map((tag) => (
              <span
                key={tag}
                className="rounded-[var(--radius-badge)] bg-slate-100 px-2 py-0.5 text-xs text-slate-600"
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        <div className="mt-auto flex items-center justify-between gap-3 pt-1">
          <span className="text-sm font-medium text-slate-500">{costDots}</span>
          <button
            type="button"
            aria-label={`${selected ? "取消选择" : "选择"} ${card.name}`}
            onClick={() => onToggle(card.id)}
            className={`
              h-9 rounded-md px-4 text-sm font-semibold transition-colors duration-[var(--transition-fast)]
              ${
                selected
                  ? "bg-teal-600 text-white hover:bg-teal-700"
                  : "border border-slate-300 bg-white text-slate-800 hover:bg-slate-50"
              }
            `}
          >
            {selected ? "已选 ✓" : "选择"}
          </button>
        </div>
      </div>
    </article>
  )
}

function CheckIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
      <path
        d="M2 6l3 3 5-5"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2"
      />
    </svg>
  )
}

function getCategoryEmoji(category: string): string {
  const emojis: Record<string, string> = {
    attraction: "🏛",
    food: "🍜",
    neighborhood: "🏘",
    activity: "🎭",
    accommodation: "🏨",
  }
  return emojis[category] ?? "📍"
}
