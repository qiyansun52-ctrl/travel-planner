import { expect, type Page } from "@playwright/test"

const FLOW_EXPECT_TIMEOUT = 15_000

export async function startFixtureTrip(page: Page, totalBudget = "6000") {
  await page.goto("/")

  await page.getByLabel("出发城市").fill("北京")
  await page.getByLabel("目的地城市").fill("上海")
  await page.getByLabel("出发日期").fill("2026-06-01")
  await page.getByLabel("旅行天数").fill("3")
  await page.getByLabel("出行人数").fill("2")
  await page.getByLabel("总预算").fill(totalBudget)
  await page.getByRole("button", { name: "开始发现灵感" }).click()

  await expect(page).toHaveURL(/\/discovery\/session_/, { timeout: FLOW_EXPECT_TIMEOUT })
  await expect(page.getByRole("heading", { name: /选择真正值得去的体验/ })).toBeVisible({
    timeout: FLOW_EXPECT_TIMEOUT,
  })
}

export async function selectDiscoveryCards(page: Page) {
  await page.getByRole("button", { name: /选择 .* waterfront walk/ }).click()
  await page.getByRole("button", { name: /选择 .* old town lanes/ }).click()
  await page.getByRole("button", { name: /选择 .* city museum/ }).click()
  await expect(page.getByRole("button", { name: /取消选择 .* waterfront walk/ })).toBeVisible()
  await expect(page.getByRole("button", { name: /取消选择 .* old town lanes/ })).toBeVisible()
  await expect(page.getByRole("button", { name: /取消选择 .* city museum/ })).toBeVisible()
  await page.getByRole("button", { name: "继续设置偏好" }).click()

  await expect(page).toHaveURL(/\/preferences\/session_/, { timeout: FLOW_EXPECT_TIMEOUT })
}

export async function submitPreferences(page: Page) {
  await page.getByLabel("住宿区域偏好").fill("中心、方便步行、附近有好吃的")
  await page.getByLabel("住宿类型").selectOption("homestay")
  await page.getByRole("button", { name: "生成完整行程" }).click()

  await expect(page).toHaveURL(/\/trips\/session_/, { timeout: FLOW_EXPECT_TIMEOUT })
  await expect(page.getByText("目的地故事", { exact: true })).toBeVisible({
    timeout: FLOW_EXPECT_TIMEOUT,
  })
  await expect(page.getByText("预算匹配", { exact: true })).toBeVisible()
  await expect(page.getByText("叙事路线", { exact: true })).toBeVisible()
  const detailedItinerary = page.getByRole("region", { name: "详细行程" })
  await expect(detailedItinerary).toBeVisible()
  await expect(detailedItinerary.getByText("每日执行", { exact: true })).toBeVisible()
}

export async function completeFixtureTrip(page: Page, totalBudget = "6000") {
  await startFixtureTrip(page, totalBudget)
  await selectDiscoveryCards(page)
  await submitPreferences(page)
}
