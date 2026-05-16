"use client"

import type { AdjustmentResponse } from "@/lib/apiClient"

interface TypeCConfirmationCardProps {
  confirmation: NonNullable<AdjustmentResponse["confirmation"]>
  onAction: (action: "replan" | "save_and_start_new" | "cancel") => void
}

export function TypeCConfirmationCard({ confirmation, onAction }: TypeCConfirmationCardProps) {
  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
      <p className="font-semibold">检测到核心行程变化</p>
      <p className="mt-2">{confirmation.detected_change}</p>
      <p className="mt-2">需要重跑：{confirmation.rerun_stages.join(", ")}</p>
      <p className="mt-1">{confirmation.discard_estimate}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        <button className="rounded-md bg-amber-900 px-3 py-2 text-white" onClick={() => onAction("replan")}>
          重新规划
        </button>
        <button className="rounded-md border border-amber-300 px-3 py-2" onClick={() => onAction("save_and_start_new")}>
          保存并新建
        </button>
        <button className="rounded-md border border-amber-300 px-3 py-2" onClick={() => onAction("cancel")}>
          取消
        </button>
      </div>
    </div>
  )
}
