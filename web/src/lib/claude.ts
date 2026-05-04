import { UserPreferences, AttractionCard } from "./types"
import { SearchItem } from "./googleSearch"

const sectionLabel: Record<AttractionCard["section"], string> = {
  experience: "体验/景点",
  transport: "交通",
  food: "美食",
}

export function buildPlanPrompt(prefs: UserPreferences): string {
  return buildPlanPromptWithAttractions(prefs, [])
}

export function buildPlanPromptWithAttractions(
  prefs: UserPreferences,
  selected: AttractionCard[]
): string {
  let attractionsSection = ""
  if (selected.length > 0) {
    const bySection = {
      experience: selected.filter((c) => c.section === "experience"),
      transport: selected.filter((c) => c.section === "transport"),
      food: selected.filter((c) => c.section === "food"),
    }
    const lines: string[] = ["\n用户已选择的感兴趣内容（请优先将这些安排进行程中）："]
    for (const [sec, cards] of Object.entries(bySection)) {
      if (cards.length === 0) continue
      lines.push(
        `【${sectionLabel[sec as AttractionCard["section"]]}】${cards
          .map((c) => `${c.name}（${c.estimatedCost}）`)
          .join("、")}`
      )
    }
    attractionsSection = lines.join("\n") + "\n"
  }

  return `你是一位专业的旅行规划师。请根据以下信息，生成一份详细的旅行规划。

目的地：${prefs.destination}
出发城市：${prefs.departureCity}
出发日期：${prefs.departureDate}
旅行天数：${prefs.days}天
总预算：¥${prefs.totalBudget}（含交通、住宿、餐饮、景点）
${attractionsSection}
住宿期待：
${prefs.accommodationDescription}

旅行体验期待：
${prefs.experienceDescription}

请生成以下内容：
1. 逐日行程（每天5-7个活动，包含时间、地点、活动描述、预计费用）
2. 预算分配（交通/住宿/餐饮/景点/其他）
3. 实用提示（3-5条，关于当地注意事项）

输出格式为 JSON，结构如下：
{
  "days": [
    {
      "day": 1,
      "date": "YYYY-MM-DD",
      "title": "今日主题",
      "activities": [
        {
          "id": "act_1_1",
          "time": "09:00",
          "endTime": "11:00",
          "place": "地点名称",
          "description": "活动描述",
          "type": "attraction|food|transport|hotel|free",
          "estimatedCost": 40,
          "tips": "注意事项（可选）"
        }
      ],
      "totalCost": 300
    }
  ],
  "budget": {
    "transport": 1200,
    "accommodation": 1800,
    "food": 1200,
    "attractions": 600,
    "other": 200,
    "total": 5000
  },
  "tips": ["提示1", "提示2", "提示3"]
}`
}

export function buildAdjustmentPrompt(
  currentPlan: string,
  userRequest: string,
  selectedAttractions: AttractionCard[] = []
): string {
  const context =
    selectedAttractions.length > 0
      ? `\n用户最初感兴趣的内容：${selectedAttractions.map((c) => c.name).join("、")}\n`
      : ""

  return `你是旅行规划助手。用户有以下调整请求：

"${userRequest}"
${context}
当前行程：
${currentPlan}

请只修改受影响的部分，保持其他内容不变。以相同的 JSON 格式返回完整的修改后行程。`
}

function formatItems(items: SearchItem[]): string {
  if (items.length === 0) return "（无搜索结果，请根据你的知识补充）"
  return items
    .map((item, i) => `[${i + 1}] ${item.title}\n    ${item.snippet}`)
    .join("\n")
}

export function buildDiscoverPrompt(
  destination: string,
  experienceItems: SearchItem[],
  transportItems: SearchItem[],
  foodItems: SearchItem[]
): string {
  return `你是一位旅游信息整理专家。根据以下三组关于「${destination}」的搜索结果，分别整理出体验景点、交通方式、美食推荐的信息卡片。

===== 体验/景点 搜索结果 =====
${formatItems(experienceItems)}

===== 交通 搜索结果 =====
${formatItems(transportItems)}

===== 美食 搜索结果 =====
${formatItems(foodItems)}

请为每个分类整理出 5–8 张信息卡片，要求：
- 内容来自搜索结果中提及最多、最具代表性的内容
- name：简洁名称，不超过15字
- description：一句话描述，不超过40字，突出亮点
- estimatedCost：预计费用，格式如 "¥50–100"、"免费" 或 "¥553（二等座）"
- tags：2–3个标签

以 JSON 格式返回，结构：
{
  "experience": [
    {
      "name": "外滩",
      "description": "上海最具代表性的滨江历史建筑群，夜景尤为壮观",
      "estimatedCost": "免费",
      "tags": ["地标", "夜景", "必去"]
    }
  ],
  "transport": [
    {
      "name": "高铁（北京→上海）",
      "description": "G字头高铁约4.5小时，是最主流的城际方案",
      "estimatedCost": "¥553（二等座）",
      "tags": ["高铁", "城际", "推荐"]
    }
  ],
  "food": [
    {
      "name": "南翔小笼包",
      "description": "豫园内百年老店，皮薄汁多，必吃经典",
      "estimatedCost": "¥30–60",
      "tags": ["小吃", "老字号", "必吃"]
    }
  ]
}`
}
