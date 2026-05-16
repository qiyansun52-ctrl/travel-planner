"""Plan prompt builders.

Python port of `web/src/lib/claude.ts::buildPlanPromptWithAttractions` and
`buildAdjustmentPrompt`.
"""

from app.models.attraction import AttractionCard
from app.models.preferences import UserPreferences

_SECTION_LABEL: dict[str, str] = {
    "experience": "体验/景点",
    "transport": "交通",
    "food": "美食",
}


def _format_selected(cards: list[AttractionCard]) -> str:
    if not cards:
        return ""
    by_section: dict[str, list[AttractionCard]] = {
        "experience": [],
        "transport": [],
        "food": [],
    }
    for c in cards:
        by_section[c.section].append(c)

    lines = ["\n用户已选择的感兴趣内容（请优先将这些安排进行程中）："]
    for section, items in by_section.items():
        if not items:
            continue
        names = "、".join(f"{c.name}（{c.estimated_cost}）" for c in items)
        lines.append(f"【{_SECTION_LABEL[section]}】{names}")
    return "\n".join(lines) + "\n"


def build_plan_prompt(prefs: UserPreferences, selected: list[AttractionCard]) -> str:
    """Prompt that turns preferences + selected cards into a day-by-day plan."""
    attractions_section = _format_selected(selected)
    return f"""你是一位专业的旅行规划师。请根据以下信息，生成一份详细的旅行规划。

目的地：{prefs.destination}
出发城市：{prefs.departure_city}
出发日期：{prefs.departure_date}
旅行天数：{prefs.days}天
总预算：¥{prefs.total_budget}（含交通、住宿、餐饮、景点）
{attractions_section}
住宿期待：
{prefs.accommodation_description}

旅行体验期待：
{prefs.experience_description}

请生成以下内容：
1. 逐日行程（每天5-7个活动，包含时间、地点、活动描述、预计费用）
2. 预算分配（交通/住宿/餐饮/景点/其他）
3. 实用提示（3-5条，关于当地注意事项）

输出格式为 JSON，结构如下：
{{
  "days": [
    {{
      "day": 1,
      "date": "YYYY-MM-DD",
      "title": "今日主题",
      "activities": [
        {{
          "id": "act_1_1",
          "time": "09:00",
          "endTime": "11:00",
          "place": "地点名称",
          "description": "活动描述",
          "type": "attraction|food|transport|hotel|free",
          "estimatedCost": 40,
          "tips": "注意事项（可选）"
        }}
      ],
      "totalCost": 300
    }}
  ],
  "budget": {{
    "transport": 1200,
    "accommodation": 1800,
    "food": 1200,
    "attractions": 600,
    "other": 200,
    "total": 5000
  }},
  "tips": ["提示1", "提示2", "提示3"]
}}"""


def build_adjustment_prompt(
    current_plan: str,
    user_request: str,
    selected: list[AttractionCard],
) -> str:
    """Prompt for AI chat-driven plan adjustments. Includes original selections as context."""
    context = (
        f"\n用户最初感兴趣的内容：{'、'.join(c.name for c in selected)}\n" if selected else ""
    )
    return f"""你是旅行规划助手。用户有以下调整请求：

"{user_request}"
{context}
当前行程：
{current_plan}

请只修改受影响的部分，保持其他内容不变。以相同的 JSON 格式返回完整的修改后行程。"""
