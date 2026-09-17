# Status

Attention: focus

## Goal

A free, open API that serves hourly electricity grid emissions intensity (gCO2eq/kWh) for EU countries, like Carbon Intensity UK but for the EU. Public repo `rdeknijf/grid-emissions-api`, live at `grid.deknijf.com`.

## Last Run

2026-09-17: STATUS.md created. Public endpoints and the beads backlog verified; no code changes.

## Current State

- Verified 2026-09-17: `GET https://grid.deknijf.com/healthz` returns `{"status":"ok"}`.
- Verified 2026-09-17: `GET /v1/intensity/latest?country=NL` returns data with `latest_timestamp` `2026-09-17T06:00:00Z` (intensity 237.8), so hourly ingest is current.
- Stack: Python 3.14, FastAPI, uv, ruff, ty, pytest. Data comes from ENTSO-E, with IPCC AR6 emission factors. Storage is SQLite on a PVC.
- Deploy (from square `context/grid-emissions/README.md`, not re-verified on the cluster): k3s on Buckland through Flux. A Deployment and an hourly CronJob run the SHA-pinned image `ghcr.io/rdeknijf/grid-emissions:<sha>`. The k3s manifests live in square `context/grid-emissions/infra/`.
- CI: `.github/workflows/build.yml` builds and pushes the image on push to `main`. No workflow runs the tests.
- Latest commits on `main`: correctness fixes (UTC query window, sub-hourly average), CORS, XXE hardening, removal of the unimplemented gap-filling claim, and the beads database (PR #6).
- Beads (prefix `grid`): 2 total, 1 open and ready, 0 in progress, 0 blocked, 1 closed.

## Decisions

- Removed the gap-filling claim from the landing page instead of an implementation, because no interpolation code exists.
- The backlog is beads; GitHub issues are the inbox and the public showcase. Push beads to GitHub only per epic or per issue with `scripts/bd-sync`.
- This repo is public: PRs start as draft (square CLAUDE.md).

## Blockers

None

## Deadlines

None

## Resume

1. Read `AGENTS.md` and `README.md` here, and square `context/grid-emissions/README.md` for the deploy.
2. Run `scripts/bd-sync pull`, then `bd ready`.
3. Run the tests with `uv run pytest -v`.
4. Check live state with `curl https://grid.deknijf.com/healthz`.
