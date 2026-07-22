# ThunderQuote Research Explorer

**Synthetic research simulator, not an insurance quote.** This repository contains Dhruv Chandna and Luke Flecker's 2024–2025 TJHSST Senior Research Project. The maintained web experience is a transparent, static explorer for a legacy generated dataset. It is not validated for insurance, lending, purchasing, underwriting, pricing, or safety decisions.

The original project combined U.S. county geography with generated claims and storm values. This contribution makes that artifact inspectable: choose a county, adjust documented classroom assumptions, and export a versioned, dimensionless Illustrative Scenario Index. The browser receives no dollar-valued fields, and scenario inputs never leave the page.

## Quick start

Prerequisites: Git and Node.js 22 (the tested version is in `.nvmrc`). The repository is a 1.5 GB research archive with a 423 MB Git pack, so a fresh clone can take time; the target below is under five minutes **after checkout**.

```sh
nvm use
npm ci
npm run dev
```

Open the URL printed by Vite, normally <http://localhost:5173>. You should see a national map, the visible synthetic-data notice, and state/county selectors. No Python environment, credentials, database, or server is required for normal UI work.

Run the complete local gate before committing:

```sh
npm run check
```

Useful commands:

| Command                    | Purpose                                                              |
| -------------------------- | -------------------------------------------------------------------- |
| `npm run dev`              | Start the local Vite server with hot reload                          |
| `npm run test`             | Run JavaScript model/serialization tests                             |
| `npm run test:e2e`         | Run Playwright keyboard, responsive, route, and accessibility checks |
| `npm run artifacts:verify` | Verify committed hashes, schemas, privacy rules, and size budgets    |
| `npm run build`            | Create the static production site in `dist/`                         |
| `npm run preview`          | Serve the built site locally                                         |
| `npm run check`            | Run formatting, lint, unit, artifact, language, and build gates      |

## Architecture

```text
frozen data_04.csv + Census shapefiles + reviewed crosswalk
                              |
                scripts/build_runtime_data.py
                (offline maintainer command)
                              |
                              v
 web/public/data/<dataset-id>/manifest + metrics + GeoJSON
                              |
                              v
        static Vite HTML/CSS/JS + browser-only calculation
                     |                     |
                     v                     v
                explorer `/`       methodology `/methodology/`
```

The production site uses vanilla JavaScript and `d3-geo`; Vercel serves only static files. Python, pandas, and GeoPandas are artifact-generation tools, not runtime dependencies. `data_04.csv` is frozen at SHA-256 `4093e523e84c9908aed438a637fda1aaebecdc439fca8bbd5540688dfa4eda13`. The packager does not rerun the unseeded legacy generator.

Read [the in-app methodology](web/methodology/index.html) for field lineage, the exact index definition, six withheld ambiguous county/city keys, limitations, and reproduction steps.

## Rebuilding runtime artifacts

Most contributors should not regenerate data. If a reviewed source, mapping, schema, or formula changes, create the pinned maintainer environment:

```sh
uv venv --python 3.12 .venv-artifacts
uv pip install --python .venv-artifacts/bin/python -r requirements-artifacts.txt
.venv-artifacts/bin/python scripts/build_runtime_data.py
python3 scripts/verify_runtime_data.py
```

The builder stages and safely replaces `web/public/data`, refuses to overwrite a directory that is not already a generated artifact set, resolves geography only through direct canonical matches or [the reviewed crosswalk](data/mappings/county_crosswalk.csv), and fails on every unreviewed mismatch. Commit generated artifacts with their source/mapping change. Never run `src/preprocessing/storm_simplifier.py` as part of this workflow; it uses unseeded randomness and represents historical research code.

## Vercel preview

The repository root is the Vercel project root. `vercel.json` builds to `dist/`, and `.vercelignore` uses an allowlist so the 1.5 GB research tree is not uploaded.

```sh
npm run check
npx --yes vercel@56.5.0 deploy --dry --format=json
npx --yes vercel@56.5.0
```

Inspect the dry-run manifest before creating a preview. It must contain the app, compact runtime artifacts, and no Python/serverless Function or raw research data. Public production promotion is intentionally not automated: the repository owners must first confirm redistribution rights, choose a software/content license, and identify a monitoring/takedown owner.

## Troubleshooting

- `npm ci` rejects the Node version: run `nvm install` and `nvm use` from the repository root.
- The page says `Dataset unavailable`: run `npm run artifacts:verify`; it names the missing, changed, or oversized artifact.
- A county partition fails: reload once, then verify artifacts. The prior state selection remains intact.
- Browser tests cannot find Chromium: run `npx playwright install chromium` and retry `npm run test:e2e`.
- A fresh clone is slow: that is inherited archive history. `.vercelignore` reduces deployment upload size, not Git history.

## Contributing and attribution

See [CONTRIBUTING.md](CONTRIBUTING.md) before editing generated files or public research claims. A current-dated commit appears on this fork when pushed with an email verified on the contributor's GitHub account. Appearing on the upstream `lukeflecker/Senior-Research` contributor list requires that upstream repository to accept the commit, normally through a pull request. Do not backdate commits or generate filler history.

## License and archive status

No repository license is currently stated. Copyright defaults therefore apply; do not assume permission to redistribute code, source data, reports, or media. The project is an archived school research artifact with a maintained static explorer. Security concerns can be reported through [SECURITY.md](SECURITY.md).
