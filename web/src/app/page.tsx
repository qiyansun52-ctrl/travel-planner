export default function HomePage() {
  return (
    <main className="min-h-screen bg-slate-50 px-6 py-12 text-slate-950">
      <section className="mx-auto flex min-h-[calc(100vh-6rem)] w-full max-w-4xl flex-col justify-center">
        <p className="mb-4 text-sm font-medium uppercase tracking-[0.18em] text-slate-500">
          Single-city travel planning
        </p>
        <h1 className="max-w-3xl text-4xl font-semibold leading-tight sm:text-5xl">
          Discover what is worth doing before building the itinerary.
        </h1>
        <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-600">
          The hard-constraint intake lands here in Task 7. Until then, this
          shell keeps the first screen focused on the approved discovery-first
          flow.
        </p>
      </section>
    </main>
  )
}
