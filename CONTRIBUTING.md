# Contributing

Thank you for improving ThunderQuote Research Explorer. Contributions should make the archived research easier to inspect, reproduce, or understand without overstating what its generated data can support.

## Before you start

1. Read the trust notice and methodology in `README.md` and `web/methodology/index.html`.
2. Use Node 22 (`nvm use`) and install the frozen dependency tree with `npm ci`.
3. Run `npm run check` before and after your change.

Normal frontend work does not need Python. Files below `web/public/data/` are generated; do not edit them by hand. A source, formula, schema, or crosswalk change must use the pinned environment in `requirements-artifacts.txt`, run `scripts/build_runtime_data.py`, and include the resulting manifest and join-report changes.

## Pull request expectations

- Keep the visible sentence “Synthetic research simulator, not an insurance quote.” on every public HTML route.
- Do not add currency-valued results, real-world severity bands, accuracy/fairness claims, or decision-use language without a new validation and rights review.
- Keep scenario inputs browser-only; do not add analytics, session replay, query-string state, or server callbacks.
- Add or update tests for model, data, interaction, accessibility, and failure-path changes.
- Describe generated artifact changes and any geography exception explicitly.
- Use ordinary current-dated commits. Never manipulate timestamps or add filler commits for graph activity.

## Generated-data policy

`data/combined/data_04.csv` is a frozen legacy synthetic input. The deterministic contract covers packaging those bytes, not recreating the historical unseeded random process. New ambiguous geography keys must fail the build until a human reviews `data/mappings/county_crosswalk.csv`. Fuzzy matching is not allowed.

## Rights

The repository currently has no stated license. Opening a contribution does not establish redistribution rights. Repository owners must make licensing and public-production decisions.
