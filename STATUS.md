# Status

Attention: focus

## Goal

A free, open API that serves hourly electricity grid emissions intensity (gCO2eq/kWh) for EU countries, like Carbon Intensity UK but for the EU. Public repo `rdeknijf/grid-emissions-api`, live at `grid.deknijf.com`.

## Last Run

2026-11-01: dependency refresh (Python 3.15 image, FastAPI 0.162, Starlette 1.10, GitHub Actions, prek hooks) and an ENTSO-E parser fix. The parser now fills A03 curves forward, skips consumption series, and drops the incomplete trailing hour.

## Current State

- Verified 2026-11-01: `GET https://grid.deknijf.com/healthz` returns `{"status":"ok"}`. `GET /v1/intensity/latest?country=NL` at 07:50 UTC returns 06:00 UTC, so the hourly ingest is current for most zones.
- Verified 2026-11-01: the cluster runs image `ghcr.io/rdeknijf/grid-emissions:b7fbd05c4f0f555279a00dcaa1db937c50f40c02` (main before the refresh) in namespace `grid-emissions`. CronJob `grid-emissions-ingest` runs at minute 5 of every hour with `--hours 3`.
- Known data gaps (2026-11-01): BG has no data after 2026-10-01T07:00Z, because ENTSO-E publishes BG about 4 to 5 hours late and the 3-hour ingest window never reaches it. MT returns no A75 data from ENTSO-E.
- ENTSO-E sends A75 as curveType A03 and adds a consumption series per fuel type for some zones. Rows ingested before the parser fix carry a skewed mix: for NL on 2026-10-31 the old parser read about 15 gCO2eq/kWh too low. The start date of the A03 format is not known. A backfill rewrites the rows.
- Stack: Python 3.15, FastAPI, uv, ruff, ty, pytest, prek. Data comes from ENTSO-E, with IPCC AR6 emission factors. Storage is SQLite on a PVC.
- CI: `.github/workflows/ci.yml` runs the prek hooks, pytest and `uv audit` on every pull request and push to `main`. `.github/workflows/build.yml` builds and pushes `ghcr.io/rdeknijf/grid-emissions:<commit sha>` on push to `main`.
- Deploy: square pins the image SHA in `context/grid-emissions/infra/` (`deployment.yaml` and `cronjob.yaml`), and Flux reconciles square `main` onto k3s on Buckland.
- Renovate: `renovate.json` is present, but the Renovate app has never opened a PR or a dependency dashboard issue on this repo. It does run on square.

## Decisions

- Removed the gap-filling claim from the landing page instead of an implementation, because no interpolation code exists.
- The backlog is beads; GitHub issues are the inbox and the public showcase. Push beads to GitHub only per epic or per issue with `scripts/bd-sync`.
- The parser drops an hour that ends after the earliest end of a lagging series (one that ends within an hour of the latest series end), instead of serving a partial mix as the latest value.

## Blockers

None

## Deadlines

None

## Resume

1. Read `AGENTS.md` and `README.md` here, and square `context/grid-emissions/README.md` for the deploy.
2. Run `scripts/bd-sync pull`, then `bd ready`.
3. Run the gate: `uv run prek run --all-files` and `uv run pytest`.
4. Check live state with `curl https://grid.deknijf.com/healthz` and `kubectl -n grid-emissions get cronjob,jobs`.
