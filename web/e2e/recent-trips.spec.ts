import { expect, test } from "@playwright/test"
import { startFixtureTrip } from "./helpers/mvpFlow"

test("resumes a recent fixture trip from the home page", async ({ page }) => {
  await startFixtureTrip(page)
  const sessionId = page.url().match(/session_[^/]+/)?.[0]
  if (!sessionId) {
    throw new Error("Expected fixture flow to create a session URL")
  }
  await page.goto("/")

  await expect(page.getByRole("heading", { name: "Recent trips" })).toBeVisible()
  await expect(page.getByText("上海").first()).toBeVisible()
  await page.locator(`a[href="/discovery/${sessionId}"]`).click()

  await expect(page).toHaveURL(/\/discovery\/session_/, { timeout: 15_000 })
  await expect(page.getByRole("heading", { name: /Choose what feels worth it/ })).toBeVisible({
    timeout: 15_000,
  })
})
