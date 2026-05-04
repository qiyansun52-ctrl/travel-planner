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
export function parseSearchItems(items: any[]): SearchItem[] {
  return items.map((item) => ({
    title: item.title ?? "",
    snippet: item.snippet ?? "",
    link: item.link ?? "",
    imageUrl:
      item.pagemap?.metatags?.[0]?.["og:image"] ??
      item.pagemap?.csthumbnail?.[0]?.src ??
      "",
  }))
}

export async function searchGoogle(
  query: string,
  apiKey: string,
  cx: string
): Promise<SearchItem[]> {
  const url = new URL("https://www.googleapis.com/customsearch/v1")
  url.searchParams.set("key", apiKey)
  url.searchParams.set("cx", cx)
  url.searchParams.set("q", query)
  url.searchParams.set("num", "8")
  url.searchParams.set("lr", "lang_zh-CN")

  const res = await fetch(url.toString())
  if (!res.ok) throw new Error(`Google CSE error: ${res.status}`)
  const data = await res.json()
  return parseSearchItems(data.items ?? [])
}
