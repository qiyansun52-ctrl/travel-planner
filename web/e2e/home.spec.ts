import { expect, test } from "@playwright/test"

test("renders the placeholder home shell", async ({ page }) => {
  await page.goto("/")

  await expect(
    page.getByRole("heading", {
      name: "Discover what is worth doing before building the itinerary.",
    })
  ).toBeVisible()
})
