export const PRESETS = Object.freeze({
  neutral: Object.freeze({
    year_built: 1982,
    stories: "2",
    square_feet: 2200,
    primary_residence: "yes",
    roof_age: 6,
    devices: [],
  }),
  resilient: Object.freeze({
    year_built: 2015,
    stories: "1",
    square_feet: 1700,
    primary_residence: "yes",
    roof_age: 2,
    devices: ["alarm", "sprinklers", "generator"],
  }),
  stress: Object.freeze({
    year_built: 1925,
    stories: "3+",
    square_feet: 4800,
    primary_residence: "no",
    roof_age: 28,
    devices: [],
  }),
});

export class ScenarioError extends Error {
  constructor(field, message) {
    super(message);
    this.name = "ScenarioError";
    this.field = field;
  }
}

function finiteNumber(value, field, [minimum, maximum]) {
  const number = Number(value);
  if (!Number.isFinite(number) || number < minimum || number > maximum) {
    throw new ScenarioError(
      field,
      `${field.replaceAll("_", " ")} must be between ${minimum} and ${maximum}.`,
    );
  }
  return number;
}

export function roundHalfAwayFromZero(value, digits = 1) {
  if (!Number.isFinite(value)) return null;
  const scale = 10 ** digits;
  return (
    (Math.sign(value) *
      Math.floor(Math.abs(value) * scale + 0.5 + Number.EPSILON)) /
    scale
  );
}

export function calculateScenario(baseIndex, input, formula) {
  if (!Number.isFinite(baseIndex) || baseIndex < 0) {
    throw new ScenarioError(
      "county",
      "The selected county has no generated index data.",
    );
  }
  const yearBuilt = finiteNumber(
    input.year_built,
    "year_built",
    formula.bounds.year_built,
  );
  const squareFeet = finiteNumber(
    input.square_feet,
    "square_feet",
    formula.bounds.square_feet,
  );
  const roofAge = finiteNumber(
    input.roof_age,
    "roof_age",
    formula.bounds.roof_age,
  );
  if (!(input.stories in formula.factors.stories)) {
    throw new ScenarioError("stories", "stories must be 1, 2, or 3+.");
  }
  if (!(input.primary_residence in formula.factors.primary_residence)) {
    throw new ScenarioError(
      "primary_residence",
      "primary residence must be yes or no.",
    );
  }
  const devices = [...new Set(input.devices ?? [])];
  const factors = {
    county_base: baseIndex / 100,
    year_built:
      1 +
      formula.factors.year_built_per_year_from_1982 *
        (yearBuilt - formula.defaults.year_built),
    stories: formula.factors.stories[input.stories],
    square_feet:
      1 +
      formula.factors.square_feet_per_foot_from_2200 *
        (squareFeet - formula.defaults.square_feet),
    primary_residence:
      formula.factors.primary_residence[input.primary_residence],
    roof_age:
      1 +
      formula.factors.roof_age_per_year_from_6 *
        (roofAge - formula.defaults.roof_age),
    protective_devices:
      formula.factors.protective_device_each ** devices.length,
  };
  if (
    Object.values(factors).some(
      (factor) => !Number.isFinite(factor) || factor <= 0,
    )
  ) {
    throw new ScenarioError(
      "scenario",
      "The selected combination produces an invalid factor. Return inputs to their documented bounds.",
    );
  }
  const multiplier = Object.entries(factors)
    .filter(([name]) => name !== "county_base")
    .reduce((product, [, factor]) => product * factor, 1);
  const value = roundHalfAwayFromZero(baseIndex * multiplier, 1);
  if (value === null)
    throw new ScenarioError("scenario", "The scenario result is not finite.");
  return Object.freeze({
    value,
    base_index: baseIndex,
    multiplier,
    factors: Object.freeze(factors),
  });
}

export function createResearchRecord({
  manifest,
  formula,
  place,
  scenario,
  result,
}) {
  return {
    kind: "thunderquote-synthetic-research-record",
    dataset_id: manifest.dataset_id,
    dataset_sha256: manifest.artifact_set_sha256,
    formula_version: formula.version,
    data_period: manifest.data_period,
    geography: { geoid: place.geoid, state: place.state, county: place.county },
    generated_inputs: {
      claims_per_year: place.claims_per_year,
      storms_per_year: place.storms_per_year,
    },
    scenario,
    result: {
      index: result.value,
      base_index: result.base_index,
      multiplier: result.multiplier,
      factors: result.factors,
    },
    limitation:
      "Synthetic research simulator; not a probability, prediction, price, or insurance quote.",
  };
}
