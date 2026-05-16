import { expect, test } from "@playwright/test"
import { completeFixtureTrip } from "./helpers/mvpFlow"

test("updates stay area after a Type B adjustment", async ({ page }) => {
  await completeFixtureTrip(page)

  await page.getByPlaceholder("描述你想调整的内容…").fill("酒店换到更安静的区域")
  await page.getByRole("button", { name: "发送" }).click()

  await expect(page.getByText(/Itinerary updated/)).toBeVisible()
  const stayAreaSwitcher = page
    .locator("section")
    .filter({ has: page.getByText("住宿区域", { exact: true }) })
    .filter({ has: page.getByRole("button", { name: "切换区域" }) })
  await expect(stayAreaSwitcher.getByRole("heading", { name: "上海 quieter residential edge" })).toBeVisible()
})
