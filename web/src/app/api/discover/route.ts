import { NextRequest, NextResponse } from "next/server"
import { GoogleGenerativeAI } from "@google/generative-ai"
import { buildDiscoverPrompt } from "@/lib/claude"
import { searchGoogle, buildSearchQueries, SearchItem } from "@/lib/googleSearch"
import { AttractionCard, DiscoverSections } from "@/lib/types"
import { nanoid } from "nanoid"

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY!)
const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" })

type RawCard = Omit<AttractionCard, "id" | "imageUrl" | "section">

function attachIds(
  cards: RawCard[],
  section: AttractionCard["section"],
  imageMap: Map<string, string>
): AttractionCard[] {
  return cards.map((card) => {
    const matchKey = [...imageMap.keys()].find((k) =>
      card.name.includes(k.slice(0, 6))
    )
    return {
      ...card,
      id: nanoid(),
      section,
      imageUrl: matchKey ? (imageMap.get(matchKey) ?? "") : "",
    }
  })
}

export async function GET(req: NextRequest) {
  const destination = req.nextUrl.searchParams.get("destination")
  if (!destination) {
    return NextResponse.json({ error: "destination is required" }, { status: 400 })
  }

  const apiKey = process.env.GOOGLE_CSE_KEY
  const cx = process.env.GOOGLE_CSE_CX
  const [q1, q2, q3] = buildSearchQueries(destination)

  let experienceItems: SearchItem[] = []
  let transportItems: SearchItem[] = []
  let foodItems: SearchItem[] = []

  if (apiKey && cx) {
    const [r1, r2, r3] = await Promise.allSettled([
      searchGoogle(q1, apiKey, cx),
      searchGoogle(q2, apiKey, cx),
      searchGoogle(q3, apiKey, cx),
    ])
    if (r1.status === "fulfilled") experienceItems = r1.value
    if (r2.status === "fulfilled") transportItems = r2.value
    if (r3.status === "fulfilled") foodItems = r3.value
  }

  const allItems = [...experienceItems, ...transportItems, ...foodItems]
  const imageMap = new Map(allItems.map((item) => [item.title, item.imageUrl]))

  const prompt = buildDiscoverPrompt(destination, experienceItems, transportItems, foodItems)

  try {
    const result = await model.generateContent(prompt)
    const raw = result.response.text()

    const jsonMatch = raw.match(/\{[\s\S]*\}/)
    if (!jsonMatch) throw new Error("Gemini returned no JSON")

    const parsed = JSON.parse(jsonMatch[0]) as {
      experience: RawCard[]
      transport: RawCard[]
      food: RawCard[]
    }

    const sections: DiscoverSections = {
      experience: attachIds(parsed.experience ?? [], "experience", imageMap),
      transport: attachIds(parsed.transport ?? [], "transport", imageMap),
      food: attachIds(parsed.food ?? [], "food", imageMap),
    }

    return NextResponse.json({ sections })
  } catch (err) {
    console.error("Discover error:", err)
    return NextResponse.json({ error: "Failed to generate cards" }, { status: 500 })
  }
}
