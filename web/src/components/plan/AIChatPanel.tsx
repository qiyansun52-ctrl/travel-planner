"use client"

import { useState, useRef, useEffect } from "react"
import { ChatMessage } from "@/lib/types"
import { Button } from "@/components/ui/Button"

interface AIChatPanelProps {
  messages: ChatMessage[]
  isGenerating: boolean
  onSend: (message: string) => void
}

export function AIChatPanel({ messages, isGenerating, onSend }: AIChatPanelProps) {
  const [input, setInput] = useState("")
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  function handleSend() {
    const text = input.trim()
    if (!text || isGenerating) return
    setInput("")
    onSend(text)
  }

  return (
    <div className="flex flex-col h-full bg-gray-50 border-r border-gray-100">
      <div className="p-4 border-b border-gray-100 bg-white">
        <h2 className="font-semibold text-gray-800 text-sm">AI 助手</h2>
        <p className="text-xs text-gray-400 mt-0.5">告诉我你想怎么调整行程</p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
              msg.role === "user"
                ? "bg-blue-600 text-white rounded-br-sm"
                : "bg-white text-gray-800 border border-gray-100 rounded-bl-sm"
            }`}>
              {msg.content}
            </div>
          </div>
        ))}

        {isGenerating && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-100 rounded-2xl rounded-bl-sm px-4 py-2.5">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-gray-300 rounded-full animate-bounce [animation-delay:0ms]" />
                <span className="w-2 h-2 bg-gray-300 rounded-full animate-bounce [animation-delay:150ms]" />
                <span className="w-2 h-2 bg-gray-300 rounded-full animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="p-4 border-t border-gray-100 bg-white">
        <div className="flex gap-2">
          <textarea
            rows={2}
            placeholder="例：把第二天改成轻松一点的安排…"
            className="flex-1 rounded-lg border border-gray-200 px-3 py-2 text-sm resize-none focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault()
                handleSend()
              }
            }}
          />
          <Button onClick={handleSend} disabled={!input.trim() || isGenerating} className="self-end">
            发送
          </Button>
        </div>
      </div>
    </div>
  )
}
