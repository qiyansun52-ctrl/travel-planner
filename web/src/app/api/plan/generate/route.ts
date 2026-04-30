import { NextRequest } from "next/server"
import { anthropic, buildPlanPrompt, buildAdjustmentPrompt } from "@/lib/claude"
import { UserPreferences } from "@/lib/types"

export async function POST(req: NextRequest) {
  const body = await req.json()
  const { preferences, currentPlan, adjustment } = body as {
    preferences?: UserPreferences
    currentPlan?: string
    adjustment?: string
  }

  const prompt =
    currentPlan && adjustment
      ? buildAdjustmentPrompt(currentPlan, adjustment)
      : buildPlanPrompt(preferences!)

  const encoder = new TextEncoder()

  const stream = new ReadableStream({
    async start(controller) {
      try {
        const response = await anthropic.messages.stream({
          model: "claude-sonnet-4-6",
          max_tokens: 4096,
          messages: [{ role: "user", content: prompt }],
        })

        for await (const chunk of response) {
          if (
            chunk.type === "content_block_delta" &&
            chunk.delta.type === "text_delta"
          ) {
            controller.enqueue(encoder.encode(chunk.delta.text))
          }
        }

        controller.close()
      } catch (err) {
        controller.error(err)
      }
    },
  })

  return new Response(stream, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Transfer-Encoding": "chunked",
    },
  })
}
