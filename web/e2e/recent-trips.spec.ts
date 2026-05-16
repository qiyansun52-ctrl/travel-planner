import { expect, test } from "@playwright/test"
import { startFixtureTrip } from "./helpers/mvpFlow"

test("resumes a recent fixture trip from the home page", async ({ page }) => {
  await startFixtureTrip(page)
  const sessionId = page.url().match(/session_[^/]+/)?.[0]
  if (!sessionId) {
    throw new Error("Expected fixture flow to create a session URL")
  }
  await page.goto("/")

  await expect(page.getByRole("heading", { name: "最近行程" })).toBeVisible()
  const tripCard = page
    .getByRole("article")
    .filter({ has: page.locator(`a[href="/discovery/${sessionId}"]`) })
  await expect(tripCard.getByRole("heading", { name: "上海" })).toBeVisible()
  await tripCard.getByRole("link", { name: "继续" }).click()

  await expect(page).toHaveURL(/\/discovery\/session_/, { timeout: 15_000 })
  await expect(page.getByRole("heading", { name: /选择真正值得去的体验/ })).toBeVisible({
    timeout: 15_000,
  })
})
