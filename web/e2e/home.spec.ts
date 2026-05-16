import { expect, test } from "@playwright/test"

test("renders the hard-constraint intake", async ({ page }) => {
  await page.goto("/")

  await expect(page.getByRole("heading", { name: "规划一趟单城市旅行" })).toBeVisible()
  await expect(page.getByLabel("出发城市")).toBeVisible()
  await expect(page.getByRole("button", { name: "开始发现灵感" })).toBeVisible()

  await page.getByRole("button", { name: "Switch to English" }).click()

  await expect(page.getByRole("heading", { name: "Plan a single-city trip" })).toBeVisible()
  await expect(page.getByLabel("Departure city")).toBeVisible()
  await expect(page.getByRole("button", { name: "Start discovering ideas" })).toBeVisible()
})
