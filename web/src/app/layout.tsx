import type { Metadata } from "next"
import { Noto_Sans_SC } from "next/font/google"
import "./globals.css"

const notoSans = Noto_Sans_SC({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
})

export const metadata: Metadata = {
  title: "旅行规划 AI",
  description: "告诉 AI 你的旅行想法，它来帮你变成清晰的计划",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN">
      <body className={notoSans.className}>{children}</body>
    </html>
  )
}
