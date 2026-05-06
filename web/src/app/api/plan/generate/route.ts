import { NextRequest } from "next/server"
import { GoogleGenerativeAI } from "@google/generative-ai"
import { buildPlanPromptWithAttractions, buildAdjustmentPrompt } from "@/lib/claude"
import { UserPreferences, AttractionCard } from "@/lib/types"

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY!)
const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" })

export async function POST(req: NextRequest) {
  const body = await req.json()
  const { preferences, selectedAttractions, currentPlan, adjustment } = body as {
    preferences?: UserPreferences
    selectedAttractions?: AttractionCard[]
    currentPlan?: string
    adjustment?: string
  }

  const prompt =
    currentPlan && adjustment
      ? buildAdjustmentPrompt(currentPlan, adjustment, selectedAttractions ?? [])
      : buildPlanPromptWithAttractions(preferences!, selectedAttractions ?? [])

  try {
    const result = await model.generateContent(prompt)
    const text = result.response.text()
    return new Response(text, {
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    })
  } catch (err) {
    console.error("Gemini error:", err)
    return new Response("生成失败，请重试", { status: 500 })
  }
}
