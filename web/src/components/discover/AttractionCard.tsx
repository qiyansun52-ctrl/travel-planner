import { AttractionCard as AttractionCardType } from "@/lib/types"

const sectionIcons: Record<AttractionCardType["section"], string> = {
  experience: "🏛️",
  transport: "🚄",
  food: "🍜",
}

interface AttractionCardProps {
  card: AttractionCardType
  selected: boolean
  onToggle: (id: string) => void
}

export function AttractionCard({ card, selected, onToggle }: AttractionCardProps) {
  return (
    <button
      type="button"
      onClick={() => onToggle(card.id)}
      className={`relative w-full text-left rounded-xl overflow-hidden border-2 transition-all ${
        selected
          ? "border-blue-500 shadow-md shadow-blue-100"
          : "border-gray-100 hover:border-gray-300"
      }`}
    >
      {selected && (
        <div className="absolute top-2 right-2 z-10 bg-blue-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold">
          ✓
        </div>
      )}

      <div className="h-28 bg-gray-100 overflow-hidden flex-shrink-0">
        {card.imageUrl ? (
          <img
            src={card.imageUrl}
            alt={card.name}
            className="w-full h-full object-cover"
            onError={(e) => {
              const target = e.target as HTMLImageElement
              target.style.display = "none"
              target.parentElement!.innerHTML = `<div class="w-full h-full flex items-center justify-center text-4xl">${sectionIcons[card.section]}</div>`
            }}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-4xl">
            {sectionIcons[card.section]}
          </div>
        )}
      </div>

      <div className="p-3">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-gray-400">{card.estimatedCost}</span>
        </div>
        <p className="font-semibold text-gray-900 text-sm leading-snug">{card.name}</p>
        <p className="text-xs text-gray-500 mt-0.5 leading-relaxed line-clamp-2">
          {card.description}
        </p>
        {card.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {card.tags.map((tag) => (
              <span
                key={tag}
                className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>
    </button>
  )
}
