import { expect, test } from "@playwright/test"
import { completeFixtureTrip } from "./helpers/mvpFlow"

test("completes the fixture-backed MVP flow", async ({ page }) => {
  await completeFixtureTrip(page)

  await page.getByLabel("调整需求").fill("把第二天下午改轻松一点")
  await page.getByRole("button", { name: "发送调整" }).click()
  await expect(page.getByText(/Itinerary updated/)).toBeVisible()
})
