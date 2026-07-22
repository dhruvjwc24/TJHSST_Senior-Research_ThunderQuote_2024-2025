import { expect, test } from "@playwright/test";

// Regression: ISSUE-001 — styled Back to U.S. button ignored its hidden state
// Found by /qa on 2026-07-22
// Report: .gstack/qa-reports/qa-report-127-0-0-1-2026-07-22.md
test("shows the national back control only after a state is selected", async ({
  page,
}) => {
  await page.goto("/");
  const backButton = page.getByRole("button", { name: "Back to U.S." });
  await expect(backButton).toBeHidden();
  await page.locator("#state-select").selectOption({ label: "Virginia" });
  await expect(page.getByText("Virginia loaded.")).toBeVisible();
  await expect(backButton).toBeVisible();
});
