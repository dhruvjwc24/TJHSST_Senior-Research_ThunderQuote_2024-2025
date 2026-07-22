const REQUIRED_MANIFEST_FIELDS = [
  "dataset_id",
  "artifact_set_sha256",
  "data_period",
  "formula_version",
  "artifacts",
  "coverage",
];

async function sha256Hex(buffer) {
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  return [...new Uint8Array(digest)]
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

async function fetchJson(url, expectedHash) {
  const response = await fetch(url, { cache: "no-cache" });
  if (!response.ok) throw new Error(`${url} returned HTTP ${response.status}`);
  const bytes = await response.arrayBuffer();
  if (expectedHash && (await sha256Hex(bytes)) !== expectedHash)
    throw new Error(`${url} failed its SHA-256 integrity check`);
  try {
    return JSON.parse(new TextDecoder().decode(bytes));
  } catch {
    throw new Error(`${url} is not valid JSON`);
  }
}

function artifactHash(manifest, path) {
  const artifact = manifest.artifacts.find((item) => item.path === path);
  if (!artifact) throw new Error(`manifest does not list ${path}`);
  return artifact.sha256;
}

function validateManifest(manifest, pointer) {
  for (const field of REQUIRED_MANIFEST_FIELDS) {
    if (!(field in manifest)) throw new Error(`manifest is missing ${field}`);
  }
  if (
    manifest.dataset_id !== pointer.dataset_id ||
    !/^[a-f0-9]{12}$/.test(manifest.dataset_id)
  ) {
    throw new Error("dataset pointer and manifest do not match");
  }
}

export async function loadDataset() {
  const pointer = await fetchJson("/data/current.json");
  const manifest = await fetchJson(pointer.manifest);
  validateManifest(manifest, pointer);
  const base = `/data/${manifest.dataset_id}`;
  const [formula, metrics, states] = await Promise.all([
    fetchJson(`${base}/formula.json`, artifactHash(manifest, "formula.json")),
    fetchJson(`${base}/metrics.json`, artifactHash(manifest, "metrics.json")),
    fetchJson(
      `${base}/states.geojson`,
      artifactHash(manifest, "states.geojson"),
    ),
  ]);
  if (
    formula.version !== manifest.formula_version ||
    metrics.schema_version !== manifest.schema_version
  ) {
    throw new Error("artifact versions are incompatible with the manifest");
  }
  const counties = new Map(
    metrics.counties.map(([geoid, baseIndex, claimsPerYear, stormsPerYear]) => [
      geoid,
      {
        geoid,
        base_index: baseIndex,
        claims_per_year: claimsPerYear,
        storms_per_year: stormsPerYear,
      },
    ]),
  );
  return {
    manifest,
    formula,
    states,
    stateMetrics: metrics.states,
    countyMetrics: counties,
    base,
  };
}

export async function loadCountyPartition(dataset, stateFips) {
  const path = `counties/${stateFips}.geojson`;
  return fetchJson(
    `${dataset.base}/${path}`,
    artifactHash(dataset.manifest, path),
  );
}
