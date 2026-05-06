export interface SearchItem {
  title: string
  snippet: string
  link: string
  imageUrl: string
}

export function buildSearchQueries(
  destination: string
): [string, string, string] {
  return [
    `${destination} 必去景点 旅游体验 攻略 2025`,
    `${destination} 交通攻略 怎么去 市内出行 交通方式`,
    `${destination} 美食推荐 必吃 餐厅 小吃 2025`,
  ]
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function parseSearchItems(results: any[]): SearchItem[] {
  return results.map((r) => ({
    title: r.title ?? "",
    snippet: r.content ?? "",
    link: r.url ?? "",
    imageUrl: "",
  }))
}

export async function searchTavily(
  query: string,
  apiKey: string
): Promise<SearchItem[]> {
  const res = await fetch("https://api.tavily.com/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      api_key: apiKey,
      query,
      search_depth: "basic",
      max_results: 8,
      include_answer: false,
    }),
  })
  if (!res.ok) throw new Error(`Tavily error: ${res.status}`)
  const data = await res.json()
  return parseSearchItems(data.results ?? [])
}
