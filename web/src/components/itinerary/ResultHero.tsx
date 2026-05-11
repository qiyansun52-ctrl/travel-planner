import type { PlanningSession } from "@/lib/types"
import {
  activeStayOption,
  destinationTags,
  heroImages,
} from "./resultPageModel"

interface ResultHeroProps {
  session: PlanningSession
}

export function ResultHero({ session }: ResultHeroProps) {
  const constraints = session.hard_constraints
  const images = heroImages(session)
  const tags = destinationTags(session).slice(0, 5)
  const stay = activeStayOption(session)
  const duration = pluralize(constraints.duration_days, "day")
  const travelers = pluralize(constraints.traveler_count, "traveler")
  const budget = formatBudget(constraints.currency, constraints.total_budget)
  const departureDate = formatDate(constraints.departure_date)
  const storyLine = stay
    ? `${duration} from ${constraints.departure_city}, with ${stay.area.name} as the stay base.`
    : `${duration} from ${constraints.departure_city}, shaped around the places worth prioritizing.`

  return (
    <section
      aria-labelledby="result-hero-title"
      className="relative isolate overflow-hidden rounded-lg border border-slate-200 bg-slate-950 text-white"
    >
      {images.length > 0 ? <HeroImageLayer images={images} /> : <HeroFallbackTexture />}
      <div className="absolute inset-0 bg-gradient-to-r from-slate-950 via-slate-950/85 to-slate-950/45" />
      <div className="absolute inset-x-0 bottom-0 h-32 bg-gradient-to-t from-slate-950/90 to-transparent" />

      <div className="relative grid gap-6 p-5 sm:p-6 lg:grid-cols-[minmax(0,1fr)_320px] lg:p-8">
        <div className="min-w-0">
          {images.length === 0 && (
            <p className="mb-3 inline-flex max-w-full rounded-md border border-white/15 bg-white/10 px-2.5 py-1 text-xs font-semibold text-slate-100 shadow-sm backdrop-blur">
              Route texture
            </p>
          )}
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-teal-100">
            Destination story
          </p>
          <h1
            id="result-hero-title"
            className="mt-3 max-w-3xl break-words text-4xl font-semibold leading-tight sm:text-5xl"
          >
            {constraints.destination_city}
          </h1>
          <p className="mt-4 max-w-2xl break-words text-sm leading-6 text-slate-100 sm:text-base sm:leading-7">
            {storyLine}
          </p>

          {tags.length > 0 && (
            <div
              aria-label="Top destination tags"
              className="mt-5 flex max-w-3xl flex-wrap gap-2"
            >
              {tags.map((tag) => (
                <span
                  key={tag}
                  className="max-w-full truncate rounded-md border border-white/15 bg-white/10 px-2.5 py-1 text-xs font-medium text-white shadow-sm backdrop-blur"
                  title={tag}
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>

        <dl className="grid min-w-0 gap-3 rounded-lg border border-white/15 bg-slate-950/55 p-4 shadow-sm backdrop-blur sm:grid-cols-2 lg:grid-cols-1">
          <HeroFact label="Duration" value={duration} />
          <HeroFact label="Departure" value={`${constraints.departure_city} - ${departureDate}`} />
          <HeroFact label="Travelers" value={travelers} />
          <HeroFact label="Budget" value={budget} />
          {stay && <HeroFact label="Stay area" value={stay.area.name} />}
        </dl>
      </div>
    </section>
  )
}

function HeroImageLayer({
  images,
}: {
  images: Array<{ alt: string; src: string }>
}) {
  const gridClass =
    images.length === 1
      ? ""
      : images.length === 2
        ? "grid-cols-2"
        : "grid-cols-2 grid-rows-2"

  return (
    <div aria-hidden="true" className={`absolute inset-0 grid ${gridClass}`}>
      {images.map((image, index) => (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          key={`${image.src}-${index}`}
          src={image.src}
          alt=""
          loading={index === 0 ? "eager" : "lazy"}
          className={`${imageClassName(index, images.length)} opacity-85`}
        />
      ))}
    </div>
  )
}

function HeroFallbackTexture() {
  return (
    <div aria-hidden="true" className="absolute inset-0 overflow-hidden bg-slate-950">
      <div
        className="absolute inset-0 opacity-80"
        style={{
          backgroundImage:
            "repeating-linear-gradient(135deg, rgba(20, 184, 166, 0.22) 0 1px, transparent 1px 42px), repeating-linear-gradient(45deg, rgba(251, 191, 36, 0.14) 0 1px, transparent 1px 64px), linear-gradient(120deg, #0f172a, #1f2937 52%, #111827)",
        }}
      />
      <div className="absolute left-[8%] top-[26%] h-px w-[34%] -rotate-12 bg-teal-200/50" />
      <div className="absolute left-[35%] top-[48%] h-px w-[38%] rotate-6 bg-amber-200/45" />
      <div className="absolute right-[10%] bottom-[24%] h-px w-[30%] -rotate-12 bg-rose-200/35" />
      <div className="absolute left-[8%] top-[24%] h-2 w-2 rounded-sm bg-teal-100/80" />
      <div className="absolute left-[34%] top-[45%] h-2 w-2 rounded-sm bg-amber-100/80" />
      <div className="absolute right-[10%] bottom-[23%] h-2 w-2 rounded-sm bg-rose-100/70" />
    </div>
  )
}

function HeroFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 border-b border-white/10 pb-3 last:border-b-0 last:pb-0">
      <dt className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-300">
        {label}
      </dt>
      <dd className="mt-1 break-words text-sm font-semibold leading-6 text-white">{value}</dd>
    </div>
  )
}

function imageClassName(index: number, count: number): string {
  const base = "h-full w-full object-cover"

  if (count === 3 && index === 0) {
    return `${base} row-span-2`
  }

  return base
}

function formatBudget(currency: string, value: number): string {
  if (value <= 0) {
    return "Budget pending"
  }

  return `${currency} ${Math.round(value).toLocaleString("en-US")}`
}

function formatDate(value: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (!match) {
    return value
  }

  const [, year, month, day] = match
  const date = new Date(Date.UTC(Number(year), Number(month) - 1, Number(day)))

  return new Intl.DateTimeFormat("en-US", {
    day: "numeric",
    month: "short",
    timeZone: "UTC",
    year: "numeric",
  }).format(date)
}

function pluralize(count: number, singular: string): string {
  return `${count} ${singular}${count === 1 ? "" : "s"}`
}
