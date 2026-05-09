import { defineConfig, devices } from "@playwright/test"

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  expect: {
    timeout: 5_000,
  },
  fullyParallel: true,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "on-first-retry",
  },
  webServer: {
    command:
      "GEMINI_API_KEY=test-gemini TAVILY_API_KEY=test-tavily E2E_FIXTURE_MODE=1 SESSION_DATA_DIR=/private/tmp/travel-planner-playwright/sessions METRICS_DATA_DIR=/private/tmp/travel-planner-playwright/metrics CORS_ORIGINS=http://127.0.0.1:3000,http://localhost:3000 NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 npm run dev",
    url: "http://127.0.0.1:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
})
