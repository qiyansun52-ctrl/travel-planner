import { expect, test } from "@playwright/test"
import { completeFixtureTrip } from "./helpers/mvpFlow"

test("updates stay area after a Type B adjustment", async ({ page }) => {
  await completeFixtureTrip(page)

  await page.getByLabel("Adjustment request").fill("酒店换到更安静的区域")
  await page.getByRole("button", { name: "Send adjustment" }).click()

  await expect(page.getByText(/Itinerary updated/)).toBeVisible()
  await expect(page.getByText("上海 quieter residential edge")).toBeVisible()
})
