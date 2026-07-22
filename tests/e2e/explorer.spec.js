import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("completes the selector journey and exports a versioned result", async ({
  page,
}) => {
  const errors = [];
  page.on(
    "console",
    (message) => message.type() === "error" && errors.push(message.text()),
  );
  await page.goto("/");
  await expect(page.getByText("Dataset verified.")).toBeVisible();
  await page.locator("#state-select").selectOption({ label: "Virginia" });
  await expect(page.getByText("Virginia loaded.")).toBeVisible();
  await page.locator("#county-select").selectOption({ label: "Loudoun" });
  await expect(
    page.getByRole("heading", { name: "Loudoun, Virginia" }),
  ).toBeVisible();
  await expect(page.locator("#result-value")).not.toHaveText("—");
  await expect(
    page.getByRole("button", { name: "Download JSON" }),
  ).toBeEnabled();
  expect(errors).toEqual([]);
});

test("keeps the newest state when partition requests finish out of order", async ({
  page,
}) => {
  await page.route("**/counties/51.geojson", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 250));
    await route.continue();
  });
  await page.goto("/");
  await expect(page.getByText("Dataset verified.")).toBeVisible();
  await page.locator("#state-select").selectOption({ label: "Virginia" });
  await page.locator("#state-select").selectOption({ label: "Maryland" });
  await expect(page.getByText("Maryland loaded.")).toBeVisible();
  await page.waitForTimeout(300);
  await expect(page.locator("#map-title")).toHaveText("Maryland counties");
  await expect(page.locator("#county-select")).toContainText("Montgomery");
  await expect(page.locator("#county-select")).not.toContainText("Loudoun");
});

test("marks an invalid scenario result as stale and disables export", async ({
  page,
}) => {
  await page.goto("/");
  await page.locator("#state-select").selectOption({ label: "Virginia" });
  await page.locator("#county-select").selectOption({ label: "Loudoun" });
  await expect(page.locator("#download-button")).toBeEnabled();
  await page.locator("#roof-age").fill("101");
  await expect(page.locator("#validation-error")).toContainText(
    "displayed value is stale",
  );
  await expect(page.locator("#download-button")).toBeDisabled();
});

test("has no serious accessibility violations and supports direct methodology navigation", async ({
  page,
}) => {
  await page.goto("/methodology/");
  await expect(
    page.getByRole("heading", { name: "How the research explorer works" }),
  ).toBeVisible();
  await expect(page.locator("#method-dataset")).not.toHaveText("loading");
  const results = await new AxeBuilder({ page }).analyze();
  expect(
    results.violations.filter((violation) =>
      ["serious", "critical"].includes(violation.impact),
    ),
  ).toEqual([]);
});
