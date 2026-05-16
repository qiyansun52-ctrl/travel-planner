"use client"

import { FormEvent, useState } from "react"
import type { Preference } from "@/lib/types"

interface PreferenceFormProps {
  onSubmit: (payload: Preference) => Promise<void> | void
}

export function PreferenceForm({ onSubmit }: PreferenceFormProps) {
  const [areaVibe, setAreaVibe] = useState("中心、方便步行、附近有好吃的")
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
    <form
      onSubmit={handleSubmit}
      className="grid w-full max-w-4xl gap-5 rounded-lg border border-slate-200 bg-white p-4 shadow-sm sm:p-5 md:grid-cols-2"
    >
      <label className="flex flex-col gap-2 text-sm font-semibold text-slate-700 md:col-span-2">
        住宿区域偏好
        <textarea
          value={areaVibe}
          onChange={(event) => setAreaVibe(event.target.value)}
          className="min-h-24 rounded-md border border-slate-300 px-3 py-2 text-base text-slate-950 outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
          required
        />
      </label>

      <Select label="安静或热闹" value={quietVsLively} onChange={setQuietVsLively}>
        <option value="quiet">更安静</option>
        <option value="balanced">均衡</option>
        <option value="lively">更热闹</option>
      </Select>

      <Select label="住宿类型" value={stayType} onChange={setStayType}>
        <option value="hotel">酒店</option>
        <option value="homestay">民宿</option>
        <option value="flexible">都可以</option>
      </Select>

      <fieldset className="flex flex-col gap-2 text-sm font-semibold text-slate-700">
        <legend className="mb-1">城际交通</legend>
        <div className="grid grid-cols-3 gap-2">
          {[
            { value: "rail", label: "高铁/火车", icon: "🚄" },
            { value: "flight", label: "飞机优先", icon: "✈️" },
            { value: "flexible", label: "都可以", icon: "🔀" },
          ].map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() =>
                setTransport(option.value as Preference["intercity_transport_preference"])
              }
              className={`
                flex flex-col items-center gap-1.5 rounded-xl border p-3 text-sm font-medium transition-colors
                ${
                  transport === option.value
                    ? "border-teal-500 bg-teal-50 text-teal-800 shadow-[0_0_0_2px_theme(colors.teal.500)]"
                    : "border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50"
                }
              `}
            >
              <span className="text-xl">{option.icon}</span>
              {option.label}
            </button>
          ))}
        </div>
      </fieldset>

      <Select label="早出发接受度" value={earlyDeparture} onChange={setEarlyDeparture}>
        <option value="low">尽量不要太早</option>
        <option value="medium">可以适中</option>
        <option value="high">能接受早出发</option>
      </Select>

      <Select label="换乘接受度" value={transferTolerance} onChange={setTransferTolerance}>
        <option value="low">尽量少换乘</option>
        <option value="medium">适中即可</option>
        <option value="high">可接受多换乘</option>
      </Select>

      <div className="flex flex-col gap-3 rounded-md border border-slate-200 bg-slate-50 p-3">
        <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
          <input
            type="checkbox"
            checked={willingToChangeHotels}
            onChange={(event) => setWillingToChangeHotels(event.target.checked)}
          />
          可以中途更换住宿
        </label>
        <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
          <input
            type="checkbox"
            checked={payMore}
            onChange={(event) => setPayMore(event.target.checked)}
          />
          愿意多花一点钱来节省时间
        </label>
      </div>

      <div className="md:col-span-2">
        <button
          type="submit"
          disabled={submitting}
          className="h-12 w-full rounded-md bg-slate-950 px-5 text-sm font-semibold text-white shadow-sm hover:bg-slate-800 disabled:bg-slate-400 sm:w-auto"
        >
          {submitting ? "正在生成..." : "生成完整行程"}
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
    <label className="flex flex-col gap-2 text-sm font-semibold text-slate-700">
      {label}
      <select
        value={value}
        onChange={(event) => onChange(event.target.value as T)}
        className="h-12 rounded-md border border-slate-300 bg-white px-3 text-base text-slate-950 outline-none transition focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
      >
        {children}
      </select>
    </label>
  )
}
