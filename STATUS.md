# Status

Attention: focus

## Goal

A free, open API that serves hourly electricity grid emissions intensity (gCO2eq/kWh) for EU countries, like Carbon Intensity UK but for the EU. Public repo `rdeknijf/grid-emissions-api`, live at `grid.deknijf.com`.

## Last Run

2026-11-01: PR #11 (dependency refresh and ENTSO-E parser fix) merged as `df4ff0a` and deployed through square PR #1021. The parser fills A03 curves forward, skips consumption series, and drops the incomplete trailing hour. PR #12 (merged as `c58b0bc`, deployed through square PR #1022) raises the lag limit for that cut from 1 to 3 hours, because the 08:28 run stored DE 07:00 at 686.9 gCO2eq/kWh from 7 fuel types. After the 09:05 UTC run, DE 07:00 reads 433.5 from 16 fuel types.

## Current State

- Verified 2026-11-01: the cluster runs image `ghcr.io/rdeknijf/grid-emissions:c58b0bc7b3e3dc6125dc53dc39c1c91230dfbab7` in namespace `grid-emissions` since about 08:45 UTC (Deployment and CronJob). Later docs-only merges build new image tags; square keeps the pin at `c58b0bc` on purpose until code changes. CronJob `grid-emissions-ingest` runs at minute 5 of every hour with `--hours 8`.
- Verified 2026-11-01: after the 08:28 UTC ingest run, NL 05:00 and 06:00 UTC read 447.8 and 443.7 gCO2eq/kWh live (436.8 and 426.9 with the old parser).
- BG has data again: the 08:28 run stored 3 BG points, and BG now reaches 02:00 UTC. ENTSO-E publishes BG about 4 to 5 hours late, which the old 3-hour window never reached. BG has no rows from 2026-10-01T08:00Z to 2026-10-31T23:00Z (verified live); a backfill fills the gap.
- MT returns no A75 data from ENTSO-E.
- ENTSO-E sends A75 as curveType A03 and adds a consumption series per fuel type for some zones. Rows ingested before the parser fix carry a skewed mix: for NL on 2026-10-31 the old parser read about 15 gCO2eq/kWh too low. The start date of the A03 format is not known. A backfill rewrites the rows.
- Stack: Python 3.15, FastAPI, uv, ruff, ty, pytest, prek. Data comes from ENTSO-E, with IPCC AR6 emission factors. Storage is SQLite on a PVC.
- CI: `.github/workflows/ci.yml` runs the prek hooks, pytest and `uv audit` on every pull request and push to `main`. `.github/workflows/build.yml` builds and pushes `ghcr.io/rdeknijf/grid-emissions:<commit sha>` on push to `main`.
- Deploy: square pins the image SHA in `context/grid-emissions/infra/` (`deployment.yaml` and `cronjob.yaml`), and Flux reconciles square `main` onto k3s on Buckland.
- Renovate: `renovate.json` is present, but the Renovate app has never opened a PR or a dependency dashboard issue on this repo. It does run on square.

## Decisions

- Removed the gap-filling claim from the landing page instead of an implementation, because no interpolation code exists.
- The backlog is beads; GitHub issues are the inbox and the public showcase. Push beads to GitHub only per epic or per issue with `scripts/bd-sync`.
- The parser drops an hour that ends after the earliest end of a lagging series (one that ends at most 3 hours before the latest series end), instead of serving a partial mix as the latest value. Observed lag between fuel types in one zone is up to 75 minutes (DE, 2026-11-01); 3 hours stays below the 8-hour ingest window, so a series that really stops delays hours but does not lose them.

## Blockers

None

## Deadlines

None

## Resume

1. Read `AGENTS.md` and `README.md` here, and square `context/grid-emissions/README.md` for the deploy.
2. Run `scripts/bd-sync pull`, then `bd ready`.
3. Run the gate: `uv run prek run --all-files` and `uv run pytest`.
4. Check live state with `curl https://grid.deknijf.com/healthz` and `kubectl -n grid-emissions get cronjob,jobs`.
