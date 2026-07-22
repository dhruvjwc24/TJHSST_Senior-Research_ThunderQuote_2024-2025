import { loadDataset } from "./data.js";

loadDataset()
  .then(({ manifest }) => {
    document.querySelector("#method-dataset").textContent = manifest.dataset_id;
    document.querySelector("#method-formula").textContent =
      manifest.formula_version;
    document.querySelector("#method-period").textContent =
      `${manifest.data_period.start}–${manifest.data_period.end}`;
    document.querySelector("#method-counties").textContent =
      manifest.coverage.published_counties.toLocaleString();
  })
  .catch(() => {
    for (const selector of [
      "#method-dataset",
      "#method-formula",
      "#method-counties",
    ]) {
      document.querySelector(selector).textContent =
        "Dataset metadata unavailable";
    }
  });
