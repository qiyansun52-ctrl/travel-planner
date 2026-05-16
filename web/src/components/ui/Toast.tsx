"use client"

import type { ToastMessage } from "./useToast"

const VARIANT_STYLES: Record<ToastMessage["variant"], string> = {
  error: "border-red-200 bg-red-50 text-red-800",
  success: "border-emerald-200 bg-emerald-50 text-emerald-800",
  info: "border-slate-200 bg-white text-slate-800",
}

interface ToastContainerProps {
  toasts: ToastMessage[]
  onDismiss: (id: number) => void
}

export function ToastContainer({ toasts, onDismiss }: ToastContainerProps) {
  if (toasts.length === 0) return null

  return (
    <div
      aria-atomic="false"
      aria-live="polite"
      className="fixed bottom-5 left-1/2 z-[60] flex -translate-x-1/2 flex-col gap-2"
    >
      {toasts.map((toast) => (
        <div
          key={toast.id}
          role="status"
          className={`flex min-w-64 max-w-sm items-center justify-between gap-4 rounded-xl border px-4 py-3 shadow-md ${VARIANT_STYLES[toast.variant]}`}
        >
          <p className="text-sm font-medium">{toast.text}</p>
          <button
            type="button"
            onClick={() => onDismiss(toast.id)}
            aria-label="关闭提示"
            className="flex-shrink-0 opacity-60 hover:opacity-100"
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  )
}
