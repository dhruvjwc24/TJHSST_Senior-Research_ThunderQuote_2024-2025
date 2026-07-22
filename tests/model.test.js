import { describe, expect, it } from "vitest";
import {
  PRESETS,
  ScenarioError,
  calculateScenario,
  createResearchRecord,
  roundHalfAwayFromZero,
} from "../web/src/model.js";

const formula = {
  version: "scenario-index-v1",
  defaults: {
    year_built: 1982,
    stories: "2",
    square_feet: 2200,
    primary_residence: "yes",
    roof_age: 6,
  },
  bounds: {
    year_built: [1900, 2026],
    square_feet: [200, 20000],
    roof_age: [0, 100],
  },
  factors: {
    year_built_per_year_from_1982: -0.005,
    stories: { 1: 0.9, 2: 1, "3+": 1.1 },
    square_feet_per_foot_from_2200: 0.0001,
    primary_residence: { yes: 1, no: 0.95 },
    roof_age_per_year_from_6: 0.01,
    protective_device_each: 0.975,
  },
};

describe("roundHalfAwayFromZero", () => {
  it("rounds positive and negative ties symmetrically", () => {
    expect(roundHalfAwayFromZero(1.25)).toBe(1.3);
    expect(roundHalfAwayFromZero(-1.25)).toBe(-1.3);
  });
  it("rejects nonfinite display values", () =>
    expect(roundHalfAwayFromZero(Infinity)).toBeNull());
});

describe("calculateScenario", () => {
  it("keeps the neutral preset at the county base", () => {
    const result = calculateScenario(100, PRESETS.neutral, formula);
    expect(result.value).toBe(100);
    expect(result.multiplier).toBe(1);
  });
  it("applies every factor and deduplicates protective devices", () => {
    const result = calculateScenario(
      120,
      { ...PRESETS.resilient, devices: ["alarm", "alarm", "generator"] },
      formula,
    );
    expect(result.value).toBe(78.2);
    expect(result.factors.protective_devices).toBeCloseTo(0.975 ** 2);
  });
  it.each([
    ["year_built", { ...PRESETS.neutral, year_built: 1899 }],
    ["square_feet", { ...PRESETS.neutral, square_feet: 0 }],
    ["roof_age", { ...PRESETS.neutral, roof_age: 101 }],
    ["stories", { ...PRESETS.neutral, stories: "tower" }],
    ["primary_residence", { ...PRESETS.neutral, primary_residence: "maybe" }],
  ])("returns an actionable error for %s", (field, input) => {
    expect(() => calculateScenario(100, input, formula)).toThrowError(
      ScenarioError,
    );
    try {
      calculateScenario(100, input, formula);
    } catch (error) {
      expect(error.field).toBe(field);
    }
  });
  it("rejects unavailable county data", () =>
    expect(() =>
      calculateScenario(Number.NaN, PRESETS.neutral, formula),
    ).toThrow("no generated index data"));
});

describe("createResearchRecord", () => {
  it("contains versioned reproduction fields without timestamps", () => {
    const result = calculateScenario(100, PRESETS.neutral, formula);
    const record = createResearchRecord({
      manifest: {
        dataset_id: "abc123abc123",
        artifact_set_sha256: "hash",
        data_period: { start: 1980, end: 2023 },
      },
      formula,
      place: {
        geoid: "51059",
        state: "Virginia",
        county: "Fairfax",
        claims_per_year: 1,
        storms_per_year: 2,
      },
      scenario: PRESETS.neutral,
      result,
    });
    expect(record.dataset_id).toBe("abc123abc123");
    expect(record.result.index).toBe(100);
    expect(record).not.toHaveProperty("exported_at");
    expect(JSON.stringify(record)).not.toContain("$");
  });
});
