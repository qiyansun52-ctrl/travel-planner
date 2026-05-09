export function PlanningProgress({ active }: { active: boolean }) {
  const steps = [
    "Discovering city highlights",
    "Recommending stay areas",
    "Analyzing transport",
    "Generating final itinerary",
  ]

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="text-lg font-semibold text-slate-950">Planning progress</h2>
      <div className="mt-3 grid gap-2 md:grid-cols-4">
        {steps.map((step) => (
          <div
            key={step}
            className={`rounded-md px-3 py-2 text-sm ${
              active ? "bg-sky-50 text-sky-900" : "bg-slate-50 text-slate-600"
            }`}
          >
            {step}
          </div>
        ))}
      </div>
    </div>
  )
}
