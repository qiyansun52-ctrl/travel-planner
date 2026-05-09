"use client"

import { FormEvent, useState } from "react"
import type { Preference } from "@/lib/types"

interface PreferenceFormProps {
  onSubmit: (payload: Preference) => Promise<void> | void
}

export function PreferenceForm({ onSubmit }: PreferenceFormProps) {
  const [areaVibe, setAreaVibe] = useState("central, walkable, good food nearby")
  const [quietVsLively, setQuietVsLively] = useState<Preference["quiet_vs_lively"]>("balanced")
  const [stayType, setStayType] = useState<Preference["stay_type"]>("hotel")
  const [willingToChangeHotels, setWillingToChangeHotels] = useState(false)
  const [transport, setTransport] = useState<Preference["intercity_transport_preference"]>("rail")
  const [earlyDeparture, setEarlyDeparture] = useState<Preference["early_departure_tolerance"]>("medium")
  const [transferTolerance, setTransferTolerance] = useState<Preference["transfer_tolerance"]>("medium")
  const [payMore, setPayMore] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    try {
      await onSubmit({
        area_vibe: areaVibe,
        quiet_vs_lively: quietVsLively,
        stay_type: stayType,
        willing_to_change_hotels: willingToChangeHotels,
        intercity_transport_preference: transport,
        early_departure_tolerance: earlyDeparture,
        transfer_tolerance: transferTolerance,
        pay_more_to_save_time: payMore,
      })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="grid w-full max-w-4xl gap-5 md:grid-cols-2">
      <label className="flex flex-col gap-2 text-sm font-medium text-slate-700 md:col-span-2">
        Area vibe
        <textarea
          value={areaVibe}
          onChange={(event) => setAreaVibe(event.target.value)}
          className="min-h-24 rounded-md border border-slate-300 px-3 py-2 text-base text-slate-950 outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
          required
        />
      </label>

      <Select label="Quiet vs lively" value={quietVsLively} onChange={setQuietVsLively}>
        <option value="quiet">Quiet</option>
        <option value="balanced">Balanced</option>
        <option value="lively">Lively</option>
      </Select>

      <Select label="Stay type" value={stayType} onChange={setStayType}>
        <option value="hotel">Hotel</option>
        <option value="homestay">Homestay</option>
        <option value="flexible">Flexible</option>
      </Select>

      <Select label="Intercity transport" value={transport} onChange={setTransport}>
        <option value="rail">Rail</option>
        <option value="flight">Flight</option>
        <option value="flexible">Flexible</option>
      </Select>

      <Select label="Early departure tolerance" value={earlyDeparture} onChange={setEarlyDeparture}>
        <option value="low">Low</option>
        <option value="medium">Medium</option>
        <option value="high">High</option>
      </Select>

      <Select label="Transfer tolerance" value={transferTolerance} onChange={setTransferTolerance}>
        <option value="low">Low</option>
        <option value="medium">Medium</option>
        <option value="high">High</option>
      </Select>

      <div className="flex flex-col gap-3 rounded-md border border-slate-200 bg-white p-3">
        <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
          <input
            type="checkbox"
            checked={willingToChangeHotels}
            onChange={(event) => setWillingToChangeHotels(event.target.checked)}
          />
          Willing to change hotels
        </label>
        <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
          <input
            type="checkbox"
            checked={payMore}
            onChange={(event) => setPayMore(event.target.checked)}
          />
          Spend more to save time
        </label>
      </div>

      <div className="md:col-span-2">
        <button
          type="submit"
          disabled={submitting}
          className="h-11 rounded-md bg-slate-950 px-5 text-sm font-semibold text-white hover:bg-slate-800 disabled:bg-slate-400"
        >
          {submitting ? "Generating..." : "Generate itinerary"}
        </button>
      </div>
    </form>
  )
}

function Select<T extends string>({
  label,
  value,
  onChange,
  children,
}: {
  label: string
  value: T
  onChange: (value: T) => void
  children: React.ReactNode
}) {
  return (
    <label className="flex flex-col gap-2 text-sm font-medium text-slate-700">
      {label}
      <select
        value={value}
        onChange={(event) => onChange(event.target.value as T)}
        className="h-11 rounded-md border border-slate-300 bg-white px-3 text-base text-slate-950 outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-100"
      >
        {children}
      </select>
    </label>
  )
}
