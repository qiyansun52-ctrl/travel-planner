"use client"

import type { DiscoveryCard as DiscoveryCardType } from "@/lib/types"
import { DiscoveryCard } from "./DiscoveryCard"
import { DiscoveryCardSkeleton } from "./DiscoveryCardSkeleton"

interface DiscoveryCardGridProps {
  cards: DiscoveryCardType[]
  selectedIds: string[]
  onToggle: (id: string) => void
  loading?: boolean
}

export function DiscoveryCardGrid({
  cards,
  selectedIds,
  onToggle,
  loading = false,
}: DiscoveryCardGridProps) {
  const selected = new Set(selectedIds)
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {loading
        ? Array.from({ length: 6 }, (_, index) => (
            <DiscoveryCardSkeleton key={index} />
          ))
        : cards.map((card) => (
            <DiscoveryCard
              key={card.id}
              card={card}
              selected={selected.has(card.id)}
              onToggle={onToggle}
            />
          ))}
    </div>
  )
}
