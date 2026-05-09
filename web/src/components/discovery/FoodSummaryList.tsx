import type { FoodSummary } from "@/lib/types"

export function FoodSummaryList({ items }: { items: FoodSummary[] }) {
  return (
    <section className="space-y-3">
      <h2 className="text-xl font-semibold text-slate-950">Food context</h2>
      <div className="grid gap-3 md:grid-cols-2">
        {items.map((item) => (
          <article key={item.id} className="rounded-lg border border-slate-200 bg-white p-4">
            <h3 className="font-semibold text-slate-950">{item.name}</h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">{item.description}</p>
          </article>
        ))}
      </div>
    </section>
  )
}
