import { expect, test } from "@playwright/test"

test("completes the fixture-backed MVP flow", async ({ page }) => {
  await page.goto("/")

  await page.getByLabel("Departure city").fill("北京")
  await page.getByLabel("Destination city").fill("上海")
  await page.getByLabel("Departure date").fill("2026-05-10")
  await page.getByLabel("Trip duration").fill("3")
  await page.getByLabel("Traveler count").fill("2")
  await page.getByLabel("Total trip budget").fill("6000")
  await page.getByRole("button", { name: "Start discovering ideas" }).click()

  await expect(page).toHaveURL(/\/discovery\/session_/)
  await expect(page.getByRole("heading", { name: /Choose what feels worth it/ })).toBeVisible()
  await page.getByRole("button", { name: /Select .* waterfront walk/ }).click()
  await page.getByRole("button", { name: /Select .* old town lanes/ }).click()
  await page.getByRole("button", { name: /Select .* city museum/ }).click()
  await page.getByRole("button", { name: "Continue to preferences" }).click()

  await expect(page).toHaveURL(/\/preferences\/session_/)
  await page.getByLabel("Area vibe").fill("central, walkable, good food nearby")
  await page.getByLabel("Stay type").selectOption("homestay")
  await page.getByRole("button", { name: "Generate itinerary" }).click()

  await expect(page).toHaveURL(/\/trips\/session_/)
  await expect(page.getByRole("heading", { name: /Your .* itinerary/ })).toBeVisible()
  await expect(page.getByText("Final budget")).toBeVisible()

  await page.getByLabel("Adjustment request").fill("把第二天下午改轻松一点")
  await page.getByRole("button", { name: "Send adjustment" }).click()
  await expect(page.getByText(/Itinerary updated/)).toBeVisible()
})
