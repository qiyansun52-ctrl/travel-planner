import { UserPreferences } from "./types"

export function buildPlanPrompt(prefs: UserPreferences): string {
  return `你是一位专业的旅行规划师。请根据以下信息，生成一份详细的旅行规划。

目的地：${prefs.destination}
出发城市：${prefs.departureCity}
出发日期：${prefs.departureDate}
旅行天数：${prefs.days}天
总预算：¥${prefs.totalBudget}（含交通、住宿、餐饮、景点）

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
  userRequest: string
): string {
  return `你是旅行规划助手。用户有以下调整请求：

"${userRequest}"

当前行程：
${currentPlan}

请只修改受影响的部分，保持其他内容不变。以相同的 JSON 格式返回完整的修改后行程。`
}
