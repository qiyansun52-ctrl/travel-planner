import type { AreaSummary } from "@/lib/types"

export function AreaImpressionList({ items }: { items: AreaSummary[] }) {
  return (
    <section className="space-y-3">
      <h2 className="text-xl font-semibold text-slate-950">区域印象</h2>
      <div className="grid gap-3 md:grid-cols-2">
        {items.map((item) => (
          <article key={item.id} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="font-semibold text-slate-950">{item.name}</h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">{item.note}</p>
            <p className="mt-3 text-xs text-slate-500">{item.vibe_tags.join(" / ")}</p>
          </article>
        ))}
      </div>
    </section>
  )
}
