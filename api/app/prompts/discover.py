"""Prompt builder for the /api/discover endpoint.

This is a Python port of `web/src/lib/claude.ts::buildDiscoverPrompt`.
"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class SearchItem(BaseModel):
    """One result from Tavily search, normalized for prompt formatting."""

    title: str
    snippet: str
    link: str
    image_url: str

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


def _format_items(items: list[SearchItem]) -> str:
    if not items:
        return "（无搜索结果，请根据你的知识补充）"
    return "\n".join(
        f"[{i + 1}] {item.title}\n    {item.snippet}" for i, item in enumerate(items)
    )


def build_discover_prompt(
    destination: str,
    experience_items: list[SearchItem],
    transport_items: list[SearchItem],
    food_items: list[SearchItem],
) -> str:
    """Build the prompt that turns three sets of search results into card JSON."""
    return f"""你是一位旅游信息整理专家。根据以下三组关于「{destination}」的搜索结果，分别整理出体验景点、交通方式、美食推荐的信息卡片。

===== 体验/景点 搜索结果 =====
{_format_items(experience_items)}

===== 交通 搜索结果 =====
{_format_items(transport_items)}

===== 美食 搜索结果 =====
{_format_items(food_items)}

请为每个分类整理出 5–8 张信息卡片，要求：
- 内容来自搜索结果中提及最多、最具代表性的内容
- name：简洁名称，不超过15字
- description：一句话描述，不超过40字，突出亮点
- estimatedCost：预计费用，格式如 "¥50–100"、"免费" 或 "¥553（二等座）"
- tags：2–3个标签

以 JSON 格式返回，结构：
{{
  "experience": [
    {{
      "name": "外滩",
      "description": "上海最具代表性的滨江历史建筑群，夜景尤为壮观",
      "estimatedCost": "免费",
      "tags": ["地标", "夜景", "必去"]
    }}
  ],
  "transport": [
    {{
      "name": "高铁（北京→上海）",
      "description": "G字头高铁约4.5小时，是最主流的城际方案",
      "estimatedCost": "¥553（二等座）",
      "tags": ["高铁", "城际", "推荐"]
    }}
  ],
  "food": [
    {{
      "name": "南翔小笼包",
      "description": "豫园内百年老店，皮薄汁多，必吃经典",
      "estimatedCost": "¥30–60",
      "tags": ["小吃", "老字号", "必吃"]
    }}
  ]
}}"""
