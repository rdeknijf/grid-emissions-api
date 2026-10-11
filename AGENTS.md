# AGENTS.md — grid-emissions-api

This repository is the Grid Intensity API. It serves hourly electricity grid emissions intensity in gCO2eq/kWh for EU countries. It is a Python project on uv, ruff, ty and pytest. It ingests generation data from the ENTSO-E Transparency Platform. It runs as a container behind `grid.deknijf.com`. Read `README.md` for the endpoints, the data sources and the local run commands.

## Issue tracking

The backlog is beads in this repository: `.beads/`, id prefix `grid`, synced with GitHub issues in `rdeknijf/grid-emissions-api`. The tracked `.beads/issues.jsonl` is the backup, and a pre-commit hook (`scripts/bd-export-hook.sh`) keeps it current on every commit. On a fresh clone, restore the working data with `bd bootstrap --yes`.

Pull at the start of a session:

```sh
scripts/bd-sync pull
```

Push only per epic, never the whole backlog:

```sh
scripts/bd-sync push --parent <epic-id>
scripts/bd-sync push --issues <id,id>
```

A bare `bd github sync` is forbidden. It pushes every bead to GitHub, and GitHub holds only what was pushed on purpose. `scripts/bd-sync` refuses a push without a scope for that reason.

GitHub issues are the INBOX, not the backlog. This repository is public, so an issue is also the showcase that outside readers see. `scripts/bd-sync pull` brings a new issue into beads, and triage does the routing.

Status vocabulary:

- `open` plus label `triage`: unrouted inbox item.
- `open`: routed and ready to pick up.
- `in_progress`: someone is on it.
- `blocked`: waiting on something.
- `blocked` plus label `needs-human`: waiting on Rutger.
- `closed`: done.

Effort is a label: `effort:XS`, `effort:S`, `effort:M`, `effort:L`, `effort:XL`.

bd's own git hooks are not installed here (`bd init --skip-hooks`), so prek keeps its hooks (`uv run prek install` installs the pre-commit and pre-push stages). `bd remember` is not used.
