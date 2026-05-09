"use client"

import { FormEvent, useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import { HardConstraints } from "@/domain/schemas"
import { createSession } from "@/lib/apiClient"

interface CityOption {
  label: string
  aliases: string[]
  city: string
  countryCode: string
  currency: string
}

const DESTINATIONS: CityOption[] = [
  { label: "上海 Shanghai", aliases: ["上海", "shanghai"], city: "上海", countryCode: "CN", currency: "CNY" },
  { label: "北京 Beijing", aliases: ["北京", "beijing"], city: "北京", countryCode: "CN", currency: "CNY" },
  { label: "Tokyo 东京", aliases: ["tokyo", "东京"], city: "Tokyo", countryCode: "JP", currency: "JPY" },
  { label: "Kuala Lumpur 吉隆坡", aliases: ["kuala lumpur", "吉隆坡"], city: "Kuala Lumpur", countryCode: "MY", currency: "MYR" },
  { label: "Paris 巴黎", aliases: ["paris", "巴黎"], city: "Paris", countryCode: "FR", currency: "EUR" },
  { label: "New York 纽约", aliases: ["new york", "纽约"], city: "New York", countryCode: "US", currency: "USD" },
]

interface HardConstraintFormProps {
  language?: IntakeLanguage
  onSubmit?: (payload: HardConstraints) => Promise<void> | void
}

export type IntakeLanguage = "en" | "zh"

const formCopy = {
  en: {
    departureCity: "Departure city",
    destinationCity: "Destination city",
    departureDate: "Departure date",
    durationDays: "Trip duration",
    travelerCount: "Traveler count",
    totalBudget: "Total trip budget",
    submit: "Start discovering ideas",
    submitting: "Starting...",
    unsupportedDestination: "Choose a supported destination so the country code is known.",
    positiveNumbers: "Duration, travelers, and budget must be positive.",
    submitError: "Could not start planning.",
  },
  zh: {
    departureCity: "出发城市",
    destinationCity: "目的地城市",
    departureDate: "出发日期",
    durationDays: "旅行天数",
    travelerCount: "出行人数",
    totalBudget: "总预算",
    submit: "开始发现灵感",
    submitting: "正在开始...",
    unsupportedDestination: "请选择支持的目的地，这样系统才能确认国家代码。",
    positiveNumbers: "旅行天数、出行人数和预算都必须大于 0。",
    submitError: "暂时无法开始规划。",
  },
} satisfies Record<IntakeLanguage, Record<string, string>>

export function HardConstraintForm({ language = "en", onSubmit }: HardConstraintFormProps) {
  const router = useRouter()
  const text = formCopy[language]
  const [departureCity, setDepartureCity] = useState("北京")
  const [destinationCity, setDestinationCity] = useState("上海")
  const [departureDate, setDepartureDate] = useState("2026-05-10")
  const [durationDays, setDurationDays] = useState(3)
  const [travelerCount, setTravelerCount] = useState(2)
  const [totalBudget, setTotalBudget] = useState(6000)
  const [error, setError] = useState("")
  const [submitting, setSubmitting] = useState(false)

  const destination = useMemo(
    () => resolveDestination(destinationCity),
    [destinationCity]
  )

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError("")

    if (!destination) {
      setError(text.unsupportedDestination)
      return
    }
    if (durationDays <= 0 || travelerCount <= 0 || totalBudget <= 0) {
      setError(text.positiveNumbers)
      return
    }

    const payload: HardConstraints = {
      departure_city: departureCity.trim(),
      destination_city: destination.city,
      destination_country_code: destination.countryCode,
      departure_date: departureDate,
      duration_days: durationDays,
      traveler_count: travelerCount,
      total_budget: totalBudget,
      currency: destination.currency,
    }

    setSubmitting(true)
    try {
      if (onSubmit) {
        await onSubmit(payload)
        return
      }

      const session = await createSession(payload)
      router.push(`/discovery/${session.session_id}`)
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : text.submitError)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="grid w-full max-w-5xl gap-5 md:grid-cols-2">
      <Field id="departure-city" label={text.departureCity}>
        <input
          id="departure-city"
          value={departureCity}
          onChange={(event) => setDepartureCity(event.target.value)}
          className="h-11 rounded-md border border-slate-300 bg-white px-3 text-base text-slate-950 outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
          required
        />
      </Field>

      <Field id="destination-city" label={text.destinationCity}>
        <input
          id="destination-city"
          list="destination-options"
          value={destinationCity}
          onChange={(event) => setDestinationCity(event.target.value)}
          className="h-11 rounded-md border border-slate-300 bg-white px-3 text-base text-slate-950 outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
          required
        />
        <datalist id="destination-options">
          {DESTINATIONS.map((city) => (
            <option key={city.label} value={city.city}>
              {city.label}
            </option>
          ))}
        </datalist>
      </Field>

      <Field id="departure-date" label={text.departureDate}>
        <input
          id="departure-date"
          type="date"
          value={departureDate}
          onChange={(event) => setDepartureDate(event.target.value)}
          className="h-11 rounded-md border border-slate-300 bg-white px-3 text-base text-slate-950 outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
          required
        />
      </Field>

      <Field id="trip-duration" label={text.durationDays}>
        <input
          id="trip-duration"
          type="number"
          min={1}
          value={durationDays}
          onChange={(event) => setDurationDays(Number(event.target.value))}
          className="h-11 rounded-md border border-slate-300 bg-white px-3 text-base text-slate-950 outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
          required
        />
      </Field>

      <Field id="traveler-count" label={text.travelerCount}>
        <input
          id="traveler-count"
          type="number"
          min={1}
          value={travelerCount}
          onChange={(event) => setTravelerCount(Number(event.target.value))}
          className="h-11 rounded-md border border-slate-300 bg-white px-3 text-base text-slate-950 outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
          required
        />
      </Field>

      <Field id="total-trip-budget" label={text.totalBudget}>
        <input
          id="total-trip-budget"
          type="number"
          min={1}
          value={totalBudget}
          onChange={(event) => setTotalBudget(Number(event.target.value))}
          className="h-11 rounded-md border border-slate-300 bg-white px-3 text-base text-slate-950 outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
          required
        />
      </Field>

      {error && (
        <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 md:col-span-2">
          {error}
        </p>
      )}

      <div className="md:col-span-2">
        <button
          type="submit"
          disabled={submitting}
          className="h-11 rounded-md bg-slate-950 px-5 text-sm font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          {submitting ? text.submitting : text.submit}
        </button>
      </div>
    </form>
  )
}

function Field({
  id,
  label,
  children,
}: {
  id: string
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="flex flex-col gap-2">
      <label className="text-sm font-medium text-slate-700" htmlFor={id}>
        {label}
      </label>
      {children}
    </div>
  )
}

function resolveDestination(input: string): CityOption | null {
  const normalized = input.trim().toLowerCase()
  return (
    DESTINATIONS.find(
      (destination) =>
        destination.city.toLowerCase() === normalized ||
        destination.label.toLowerCase() === normalized ||
        destination.aliases.includes(normalized)
    ) ?? null
  )
}
