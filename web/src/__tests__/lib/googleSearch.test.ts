import { buildSearchQueries, parseSearchItems } from "@/lib/googleSearch"

describe("buildSearchQueries", () => {
  it("returns exactly 3 queries", () => {
    const queries = buildSearchQueries("上海")
    expect(queries).toHaveLength(3)
  })

  it("all queries contain the destination", () => {
    const queries = buildSearchQueries("北京")
    queries.forEach((q) => expect(q).toContain("北京"))
  })

  it("query[0] targets experiences and attractions", () => {
    const [q] = buildSearchQueries("成都")
    expect(q).toMatch(/景点|体验|攻略/)
  })

  it("query[1] targets transport and getting around", () => {
    const [, q] = buildSearchQueries("成都")
    expect(q).toMatch(/交通|出行|怎么去/)
  })

  it("query[2] targets food and restaurants", () => {
    const [, , q] = buildSearchQueries("成都")
    expect(q).toMatch(/美食|餐厅|必吃/)
  })
})

describe("parseSearchItems", () => {
  it("extracts title, snippet, and link from Tavily result format", () => {
    const mockResults = [
      {
        title: "外滩夜景攻略",
        content: "上海最著名的景点之一",
        url: "https://example.com",
      },
    ]
    const result = parseSearchItems(mockResults)
    expect(result).toHaveLength(1)
    expect(result[0].title).toBe("外滩夜景攻略")
    expect(result[0].snippet).toBe("上海最著名的景点之一")
    expect(result[0].link).toBe("https://example.com")
    expect(result[0].imageUrl).toBe("")
  })

  it("handles missing fields gracefully", () => {
    const mockResults = [{ title: "豫园" }]
    const result = parseSearchItems(mockResults)
    expect(result[0].title).toBe("豫园")
    expect(result[0].snippet).toBe("")
    expect(result[0].link).toBe("")
    expect(result[0].imageUrl).toBe("")
  })

  it("returns empty array for empty input", () => {
    expect(parseSearchItems([])).toHaveLength(0)
  })
})
