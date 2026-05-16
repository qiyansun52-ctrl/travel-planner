import { expect, test } from "@playwright/test"
import {
  selectDiscoveryCards,
  startFixtureTrip,
  submitPreferences,
} from "./helpers/mvpFlow"

test("surfaces budget warning and overrun issue for a low-budget fixture trip", async ({
  page,
}) => {
  await startFixtureTrip(page, "500")

  await expect(page.getByText(/预算提醒/)).toBeVisible()

  await selectDiscoveryCards(page)
  await submitPreferences(page)

  await expect(page.getByText(/BUDGET_OVERRUN/).first()).toBeVisible()
})
