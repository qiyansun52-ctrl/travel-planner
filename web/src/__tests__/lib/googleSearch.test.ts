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
  it("extracts title, snippet, link, and og:image", () => {
    const mockItems = [
      {
        title: "外滩夜景攻略",
        snippet: "上海最著名的景点之一",
        link: "https://example.com",
        pagemap: {
          metatags: [{ "og:image": "https://example.com/img.jpg" }],
        },
      },
    ]
    const result = parseSearchItems(mockItems)
    expect(result).toHaveLength(1)
    expect(result[0].title).toBe("外滩夜景攻略")
    expect(result[0].snippet).toBe("上海最著名的景点之一")
    expect(result[0].link).toBe("https://example.com")
    expect(result[0].imageUrl).toBe("https://example.com/img.jpg")
  })

  it("falls back to csthumbnail when og:image absent", () => {
    const mockItems = [
      {
        title: "豫园",
        snippet: "古典园林",
        link: "https://x.com",
        pagemap: { csthumbnail: [{ src: "https://x.com/thumb.jpg" }] },
      },
    ]
    const result = parseSearchItems(mockItems)
    expect(result[0].imageUrl).toBe("https://x.com/thumb.jpg")
  })

  it("returns empty imageUrl when pagemap is absent", () => {
    const mockItems = [{ title: "南京路", snippet: "步行街", link: "https://x.com" }]
    const result = parseSearchItems(mockItems)
    expect(result[0].imageUrl).toBe("")
  })
})
