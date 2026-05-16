import { useCallback, useState } from "react"

export interface ToastMessage {
  id: number
  text: string
  variant: "error" | "success" | "info"
}

let nextId = 0

export function useToast() {
  const [toasts, setToasts] = useState<ToastMessage[]>([])

  const toast = useCallback(
    (text: string, variant: ToastMessage["variant"] = "info") => {
      const id = ++nextId
      setToasts((previous) => [...previous, { id, text, variant }])
      setTimeout(() => {
        setToasts((previous) => previous.filter((item) => item.id !== id))
      }, 4000)
    },
    [],
  )

  const dismiss = useCallback((id: number) => {
    setToasts((previous) => previous.filter((item) => item.id !== id))
  }, [])

  return { toasts, toast, dismiss }
}
