"use client"

import { FormEvent, useRef, useState } from "react"
import { submitAdjustment, type AdjustmentResponse } from "@/lib/apiClient"
import type { PlanningSession } from "@/lib/types"
import { TypeCConfirmationCard } from "./TypeCConfirmationCard"

interface ChatMessage {
  role: "user" | "assistant"
  text: string
  timestamp: string
}

interface AdjustmentPanelProps {
  session: PlanningSession
  onSessionChange: (session: PlanningSession) => void
}

export function AdjustmentPanel({ session, onSessionChange }: AdjustmentPanelProps) {
  const [message, setMessage] = useState("")
  const [history, setHistory] = useState<ChatMessage[]>([])
  const [sending, setSending] = useState(false)
  const [pendingConfirmation, setPendingConfirmation] = useState<AdjustmentResponse | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  function pushMessage(role: ChatMessage["role"], text: string) {
    setHistory((previous) => [
      ...previous,
      {
        role,
        text,
        timestamp: new Date().toLocaleTimeString("zh-CN", {
          hour: "2-digit",
          minute: "2-digit",
        }),
      },
    ])
  }

  async function send(action?: "replan" | "save_and_start_new" | "cancel") {
    const trimmed = message.trim()
    if (!trimmed && !action) return

    setSending(true)
    if (trimmed) {
      pushMessage("user", trimmed)
      setMessage("")
    }

    try {
      const response = await submitAdjustment({
        sessionId: session.session_id,
        message: trimmed,
        typeCAction: action,
      })
      onSessionChange(response.session)
      pushMessage("assistant", response.message)
      setPendingConfirmation(response.confirmation ? response : null)
    } catch {
      pushMessage("assistant", "调整失败，请重试。")
    } finally {
      setSending(false)
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await send()
  }

  const quickPrompts = ["换一个景点", "调整预算分配", "缩短某天行程"]

  return (
    <section className="flex flex-col rounded-xl border border-slate-200 bg-white shadow-sm">
      <header className="border-b border-slate-100 px-4 py-3">
        <h2 className="text-sm font-semibold text-slate-950">调整行程</h2>
        <p className="text-xs text-slate-500">告诉我哪里不满意，我来修改</p>
      </header>

      {history.length > 0 && (
        <div className="max-h-64 space-y-3 overflow-y-auto px-4 py-3">
          {history.map((item, index) => (
            <div
              key={`${item.timestamp}-${index}`}
              className={`flex gap-2 ${item.role === "user" ? "flex-row-reverse" : "flex-row"}`}
            >
              <div
                className={`
                  max-w-[85%] rounded-xl px-3 py-2 text-sm leading-6
                  ${
                    item.role === "user"
                      ? "rounded-tr-sm bg-teal-600 text-white"
                      : "rounded-tl-sm bg-slate-100 text-slate-800"
                  }
                `}
              >
                <p>{item.text}</p>
                <p
                  className={`mt-1 text-[10px] ${
                    item.role === "user" ? "text-right text-teal-100" : "text-slate-400"
                  }`}
                >
                  {item.timestamp}
                </p>
              </div>
            </div>
          ))}

          {sending && (
            <div className="flex gap-2">
              <div className="rounded-xl rounded-tl-sm bg-slate-100 px-4 py-3">
                <TypingDots />
              </div>
            </div>
          )}
        </div>
      )}

      {history.length === 0 && !sending && (
        <div className="flex flex-wrap gap-2 px-4 py-3">
          {quickPrompts.map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => {
                setMessage(prompt)
                textareaRef.current?.focus()
              }}
              className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-600 transition-colors hover:bg-slate-100"
            >
              {prompt}
            </button>
          ))}
        </div>
      )}

      {pendingConfirmation?.confirmation && (
        <div className="border-t border-slate-100 px-4 py-3">
          <TypeCConfirmationCard
            confirmation={pendingConfirmation.confirmation}
            onAction={(action) => void send(action)}
          />
        </div>
      )}

      <form onSubmit={handleSubmit} className="border-t border-slate-100 p-3">
        <div className="flex items-end gap-2">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault()
                void send()
              }
            }}
            placeholder="描述你想调整的内容…"
            aria-label="调整需求"
            rows={2}
            disabled={sending}
            className="
              flex-1 resize-none rounded-xl border border-slate-200 px-3 py-2 text-sm
              text-slate-950 placeholder:text-slate-400
              outline-none focus:border-teal-400 focus:ring-2 focus:ring-teal-50
              disabled:opacity-50
            "
          />
          <button
            type="submit"
            disabled={sending || !message.trim()}
            aria-label="发送"
            className="
              flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl
              bg-teal-600 text-white transition-colors
              hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-40
            "
          >
            <SendIcon />
          </button>
        </div>
        <p className="mt-1.5 text-[10px] text-slate-400">Enter 发送 · Shift+Enter 换行</p>
      </form>
    </section>
  )
}

function TypingDots() {
  return (
    <span className="flex h-4 items-center gap-1" aria-label="AI 正在思考">
      {[0, 1, 2].map((index) => (
        <span
          key={index}
          className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400"
          style={{ animationDelay: `${index * 150}ms` }}
        />
      ))}
    </span>
  )
}

function SendIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2"
      />
    </svg>
  )
}
