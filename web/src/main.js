import { loadCountyPartition, loadDataset } from "./data.js";
import { renderMap } from "./map.js";
import {
  PRESETS,
  ScenarioError,
  calculateScenario,
  createResearchRecord,
} from "./model.js";

const elements = Object.fromEntries(
  [
    "app-status",
    "map",
    "map-title",
    "back-button",
    "state-select",
    "county-select",
    "place-summary",
    "place-name",
    "claims-value",
    "storms-value",
    "preset-select",
    "scenario-form",
    "year-built",
    "stories",
    "square-feet",
    "roof-age",
    "primary-residence",
    "result-value",
    "result-explanation",
    "validation-error",
    "factor-list",
    "copy-button",
    "download-button",
    "export-fallback",
    "dataset-id",
    "formula-version",
    "data-period",
  ].map((id) => [id, document.querySelector(`#${id}`)]),
);

const state = {
  dataset: null,
  stateFeature: null,
  countyFeature: null,
  countyGeojson: null,
  currentResult: null,
  currentRecord: null,
  stateRequest: 0,
};

function setStatus(message, type = "ready") {
  elements["app-status"].textContent = message;
  elements["app-status"].dataset.state = type;
}

function featureLabel(feature) {
  return feature.properties.name;
}

function renderNationalMap() {
  renderMap(elements.map, state.dataset.states, {
    valueFor: (feature) =>
      state.dataset.stateMetrics[feature.properties.state_fips],
    labelFor: (feature) => `${feature.properties.name}: select state`,
    onSelect: (feature) => selectState(feature.properties.state_fips),
  });
}

function renderCountyMap() {
  renderMap(elements.map, state.countyGeojson, {
    valueFor: (feature) =>
      state.dataset.countyMetrics.get(feature.properties.geoid)?.base_index,
    labelFor: (feature) => {
      const available = state.dataset.countyMetrics.has(
        feature.properties.geoid,
      )
        ? "select county"
        : "generated data unavailable";
      return `${feature.properties.name}: ${available}`;
    },
    onSelect: (feature) => selectCounty(feature.properties.geoid),
  });
}

function clearCounty() {
  state.countyFeature = null;
  state.currentResult = null;
  state.currentRecord = null;
  elements["county-select"].value = "";
  elements["place-summary"].hidden = true;
  elements["result-value"].textContent = "—";
  elements["result-explanation"].textContent =
    "Choose a county to calculate a result.";
  elements["factor-list"].replaceChildren();
  elements["copy-button"].disabled = true;
  elements["download-button"].disabled = true;
  elements["validation-error"].hidden = true;
}

async function selectState(stateFips) {
  const feature = state.dataset.states.features.find(
    (item) => item.properties.state_fips === stateFips,
  );
  if (!feature) return;
  const request = ++state.stateRequest;
  state.stateFeature = feature;
  clearCounty();
  elements["state-select"].value = stateFips;
  elements["map-title"].textContent = `${feature.properties.name} counties`;
  elements["back-button"].hidden = false;
  elements["county-select"].disabled = true;
  elements["county-select"].innerHTML =
    '<option value="">Loading counties…</option>';
  setStatus(`Loading the ${feature.properties.name} county partition…`);
  try {
    const countyGeojson = await loadCountyPartition(state.dataset, stateFips);
    if (request !== state.stateRequest) return;
    state.countyGeojson = countyGeojson;
    elements["county-select"].replaceChildren(
      new Option("Choose a county", ""),
    );
    for (const county of [...state.countyGeojson.features].sort((a, b) =>
      featureLabel(a).localeCompare(featureLabel(b)),
    )) {
      const available = state.dataset.countyMetrics.has(
        county.properties.geoid,
      );
      const option = new Option(
        `${county.properties.name}${available ? "" : " — unavailable"}`,
        county.properties.geoid,
      );
      option.disabled = !available;
      elements["county-select"].append(option);
    }
    elements["county-select"].disabled = false;
    renderCountyMap();
    setStatus(
      `${feature.properties.name} loaded. Choose a county on the map or with the selector.`,
    );
  } catch (error) {
    if (request !== state.stateRequest) return;
    state.countyGeojson = null;
    elements["county-select"].innerHTML =
      '<option value="">County detail unavailable</option>';
    setStatus(
      `County detail unavailable — the ${feature.properties.name} partition could not be loaded. Retry or return to the U.S. view.`,
      "error",
    );
    console.error(error);
  }
}

function selectedScenario() {
  const deviceInputs = [
    ...elements["scenario-form"].querySelectorAll(
      'input[name="devices"]:checked',
    ),
  ];
  return {
    year_built: elements["year-built"].value,
    stories: elements.stories.value,
    square_feet: elements["square-feet"].value,
    primary_residence: elements["primary-residence"].value,
    roof_age: elements["roof-age"].value,
    devices: deviceInputs.map((input) => input.value).sort(),
  };
}

function showFactors(factors) {
  const labels = {
    county_base: "County generated-data baseline",
    year_built: "Year built",
    stories: "Stories",
    square_feet: "Square feet",
    primary_residence: "Primary residence",
    roof_age: "Roof age",
    protective_devices: "Protective devices",
  };
  elements["factor-list"].replaceChildren(
    ...Object.entries(factors).map(([name, value]) => {
      const wrapper = document.createElement("div");
      const term = document.createElement("dt");
      const detail = document.createElement("dd");
      term.textContent = labels[name] ?? name;
      detail.textContent = `× ${value.toFixed(3)}`;
      wrapper.append(term, detail);
      return wrapper;
    }),
  );
}

function updateResult() {
  if (!state.countyFeature) return;
  const metric = state.dataset.countyMetrics.get(
    state.countyFeature.properties.geoid,
  );
  try {
    const scenario = selectedScenario();
    const result = calculateScenario(
      metric.base_index,
      scenario,
      state.dataset.formula,
    );
    const place = {
      ...metric,
      state: state.stateFeature.properties.name,
      county: state.countyFeature.properties.name,
    };
    state.currentResult = result;
    state.currentRecord = createResearchRecord({
      manifest: state.dataset.manifest,
      formula: state.dataset.formula,
      place,
      scenario,
      result,
    });
    elements["result-value"].textContent = result.value.toFixed(1);
    elements["result-explanation"].textContent =
      "Relative to the versioned synthetic reference of 100. Inspect the factors before interpreting differences.";
    elements["validation-error"].hidden = true;
    elements["copy-button"].disabled = false;
    elements["download-button"].disabled = false;
    showFactors(result.factors);
  } catch (error) {
    state.currentResult = null;
    state.currentRecord = null;
    elements["validation-error"].textContent =
      `Scenario needs attention — ${error instanceof ScenarioError ? error.message : "unexpected calculation error"} The displayed value is stale and export is disabled.`;
    elements["validation-error"].hidden = false;
    elements["copy-button"].disabled = true;
    elements["download-button"].disabled = true;
  }
}

function selectCounty(geoid) {
  const feature = state.countyGeojson?.features.find(
    (item) => item.properties.geoid === geoid,
  );
  const metric = state.dataset.countyMetrics.get(geoid);
  if (!feature || !metric) return;
  state.countyFeature = feature;
  elements["county-select"].value = geoid;
  elements["place-summary"].hidden = false;
  elements["place-name"].textContent =
    `${feature.properties.name}, ${state.stateFeature.properties.name}`;
  elements["claims-value"].textContent = metric.claims_per_year.toLocaleString(
    undefined,
    { maximumFractionDigits: 1 },
  );
  elements["storms-value"].textContent = metric.storms_per_year.toLocaleString(
    undefined,
    { maximumFractionDigits: 1 },
  );
  updateResult();
  setStatus(
    `${feature.properties.name} selected. The scenario result is ready.`,
  );
}

function applyPreset(name) {
  const preset = PRESETS[name] ?? PRESETS.neutral;
  elements["year-built"].value = preset.year_built;
  elements.stories.value = preset.stories;
  elements["square-feet"].value = preset.square_feet;
  elements["primary-residence"].value = preset.primary_residence;
  elements["roof-age"].value = preset.roof_age;
  for (const input of elements["scenario-form"].querySelectorAll(
    'input[name="devices"]',
  )) {
    input.checked = preset.devices.includes(input.value);
  }
  updateResult();
}

function researchRecordJson() {
  return `${JSON.stringify(state.currentRecord, null, 2)}\n`;
}

async function copyRecord() {
  try {
    await navigator.clipboard.writeText(researchRecordJson());
    elements["copy-button"].textContent = "Copied";
    setTimeout(
      () => (elements["copy-button"].textContent = "Copy research record"),
      1500,
    );
  } catch {
    elements["export-fallback"].value = researchRecordJson();
    elements["export-fallback"].hidden = false;
    elements["export-fallback"].focus();
    elements["export-fallback"].select();
    setStatus(
      "Clipboard access was denied. The research record is selected below; copy it or use Download JSON.",
      "error",
    );
  }
}

function downloadRecord() {
  const blob = new Blob([researchRecordJson()], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `thunderquote-${state.currentRecord.geography.geoid}-${state.currentRecord.dataset_id}.json`;
  anchor.click();
  URL.revokeObjectURL(url);
}

function returnNational() {
  state.stateRequest += 1;
  state.stateFeature = null;
  state.countyGeojson = null;
  elements["state-select"].value = "";
  elements["county-select"].disabled = true;
  elements["county-select"].innerHTML =
    '<option value="">Choose a state first</option>';
  elements["map-title"].textContent = "United States";
  elements["back-button"].hidden = true;
  clearCounty();
  renderNationalMap();
  setStatus(
    "National view restored. Choose a state on the map or with the selector.",
  );
}

async function start() {
  applyPreset("neutral");
  try {
    state.dataset = await loadDataset();
    const sortedStates = [...state.dataset.states.features].sort((a, b) =>
      featureLabel(a).localeCompare(featureLabel(b)),
    );
    for (const feature of sortedStates) {
      elements["state-select"].append(
        new Option(feature.properties.name, feature.properties.state_fips),
      );
    }
    elements["dataset-id"].textContent = state.dataset.manifest.dataset_id;
    elements["formula-version"].textContent = state.dataset.formula.version;
    elements["data-period"].textContent =
      `${state.dataset.manifest.data_period.start}–${state.dataset.manifest.data_period.end}`;
    renderNationalMap();
    setStatus(
      "Dataset verified. Choose a state on the map or with the selector.",
    );
  } catch (error) {
    setStatus(
      "Dataset unavailable — manifest could not be verified. Retry once or run npm run artifacts:verify.",
      "error",
    );
    elements["state-select"].disabled = true;
    console.error(error);
  }
}

elements["state-select"].addEventListener("change", (event) =>
  event.target.value ? selectState(event.target.value) : returnNational(),
);
elements["county-select"].addEventListener(
  "change",
  (event) => event.target.value && selectCounty(event.target.value),
);
elements["back-button"].addEventListener("click", returnNational);
elements["preset-select"].addEventListener("change", (event) =>
  applyPreset(event.target.value),
);
elements["scenario-form"].addEventListener("input", updateResult);
elements["copy-button"].addEventListener("click", copyRecord);
elements["download-button"].addEventListener("click", downloadRecord);

let resizeTimer;
window.addEventListener("resize", () => {
  window.clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    if (state.countyGeojson) renderCountyMap();
    else if (state.dataset) renderNationalMap();
  }, 120);
});

start();
