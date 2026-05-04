import { AttractionCard as AttractionCardType } from "@/lib/types"
import { AttractionCard } from "./AttractionCard"

interface SectionConfig {
  icon: string
  label: string
  color: string
  emptyHint: string
}

const sectionConfig: Record<AttractionCardType["section"], SectionConfig> = {
  experience: {
    icon: "🏛️",
    label: "体验 & 景点",
    color: "bg-blue-500",
    emptyHint: "暂无景点信息",
  },
  transport: {
    icon: "🚄",
    label: "交通方式",
    color: "bg-emerald-500",
    emptyHint: "暂无交通信息",
  },
  food: {
    icon: "🍜",
    label: "美食推荐",
    color: "bg-orange-500",
    emptyHint: "暂无美食信息",
  },
}

interface SectionBlockProps {
  section: AttractionCardType["section"]
  cards: AttractionCardType[]
  selected: Set<string>
  onToggle: (id: string) => void
}

export function SectionBlock({ section, cards, selected, onToggle }: SectionBlockProps) {
  const cfg = sectionConfig[section]

  return (
    <section>
      <div className="flex items-center gap-3 mb-4">
        <div className={`w-1 h-6 rounded-full ${cfg.color}`} />
        <span className="text-lg">{cfg.icon}</span>
        <h2 className="font-bold text-gray-900 text-lg">{cfg.label}</h2>
        <span className="text-sm text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
          {cards.length} 个
        </span>
      </div>

      {cards.length === 0 ? (
        <p className="text-gray-400 text-sm py-6 text-center">{cfg.emptyHint}</p>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {cards.map((card) => (
            <AttractionCard
              key={card.id}
              card={card}
              selected={selected.has(card.id)}
              onToggle={onToggle}
            />
          ))}
        </div>
      )}
    </section>
  )
}
