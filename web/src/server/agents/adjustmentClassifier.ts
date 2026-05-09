import { AdjustmentRequest } from "@/domain/schemas"

export function classifyAdjustment(rawText: string): AdjustmentRequest {
  const text = rawText.trim()
  const lower = text.toLowerCase()

  if (!text || text.length < 4) {
    return base(text, "unknown", 0.2, "none", null)
  }

  if (/(预算|天数|人数|目的地|出发日期|departure|budget|destination|traveler|duration)/i.test(text)) {
    return base(text, "C", 0.86, rootScope(lower), text)
  }

  if (/(酒店|住宿|住|hotel|stay|area|区域|民宿|homestay)/i.test(text)) {
    return base(text, "B", 0.82, "stay", text)
  }

  if (/(交通|高铁|火车|飞机|航班|rail|train|flight|transport)/i.test(text)) {
    return base(text, "B", 0.82, "transport", text)
  }

  if (/(轻松|紧凑|换|删除|添加|第二天|下午|itinerary|plan|day)/i.test(text)) {
    return base(text, "A", 0.78, "day", text)
  }

  return base(text, "unknown", 0.45, "none", null)
}

function base(
  raw_text: string,
  type: AdjustmentRequest["type"],
  confidence: number,
  target_scope: AdjustmentRequest["target_scope"],
  proposed_change: string | null
): AdjustmentRequest {
  return { raw_text, type, confidence, target_scope, proposed_change }
}

function rootScope(text: string): AdjustmentRequest["target_scope"] {
  if (/(budget|预算)/i.test(text)) return "budget"
  if (/(duration|天数)/i.test(text)) return "duration"
  if (/(destination|目的地)/i.test(text)) return "destination"
  if (/(traveler|人数)/i.test(text)) return "traveler_count"
  return "none"
}
