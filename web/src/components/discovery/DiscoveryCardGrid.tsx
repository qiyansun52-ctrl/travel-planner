"use client"

import { DiscoveryCard as DiscoveryCardType } from "@/domain/schemas"
import { DiscoveryCard } from "./DiscoveryCard"

interface DiscoveryCardGridProps {
  cards: DiscoveryCardType[]
  selectedIds: string[]
  onToggle: (id: string) => void
}

export function DiscoveryCardGrid({ cards, selectedIds, onToggle }: DiscoveryCardGridProps) {
  const selected = new Set(selectedIds)
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {cards.map((card) => (
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
