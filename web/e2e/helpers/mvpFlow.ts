import { expect, type Page } from "@playwright/test"

const FLOW_EXPECT_TIMEOUT = 15_000

export async function startFixtureTrip(page: Page, totalBudget = "6000") {
  await page.goto("/")

  await page.getByLabel("Departure city").fill("北京")
  await page.getByLabel("Destination city").fill("上海")
  await page.getByLabel("Departure date").fill("2026-05-10")
  await page.getByLabel("Trip duration").fill("3")
  await page.getByLabel("Traveler count").fill("2")
  await page.getByLabel("Total trip budget").fill(totalBudget)
  await page.getByRole("button", { name: "Start discovering ideas" }).click()

  await expect(page).toHaveURL(/\/discovery\/session_/, { timeout: FLOW_EXPECT_TIMEOUT })
  await expect(page.getByRole("heading", { name: /Choose what feels worth it/ })).toBeVisible({
    timeout: FLOW_EXPECT_TIMEOUT,
  })
}

export async function selectDiscoveryCards(page: Page) {
  await page.getByRole("button", { name: /Select .* waterfront walk/ }).click()
  await page.getByRole("button", { name: /Select .* old town lanes/ }).click()
  await page.getByRole("button", { name: /Select .* city museum/ }).click()
  await expect(page.getByRole("button", { name: /Unselect .* waterfront walk/ })).toBeVisible()
  await expect(page.getByRole("button", { name: /Unselect .* old town lanes/ })).toBeVisible()
  await expect(page.getByRole("button", { name: /Unselect .* city museum/ })).toBeVisible()
  await page.getByRole("button", { name: "Continue to preferences" }).click()

  await expect(page).toHaveURL(/\/preferences\/session_/, { timeout: FLOW_EXPECT_TIMEOUT })
}

export async function submitPreferences(page: Page) {
  await page.getByLabel("Area vibe").fill("central, walkable, good food nearby")
  await page.getByLabel("Stay type").selectOption("homestay")
  await page.getByRole("button", { name: "Generate itinerary" }).click()

  await expect(page).toHaveURL(/\/trips\/session_/, { timeout: FLOW_EXPECT_TIMEOUT })
  await expect(page.getByRole("heading", { name: /Your .* itinerary/ })).toBeVisible({
    timeout: FLOW_EXPECT_TIMEOUT,
  })
  await expect(page.getByText("Final budget")).toBeVisible()
}

export async function completeFixtureTrip(page: Page, totalBudget = "6000") {
  await startFixtureTrip(page, totalBudget)
  await selectDiscoveryCards(page)
  await submitPreferences(page)
}
