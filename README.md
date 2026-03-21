# Grid Intensity API

Free, open API serving hourly electricity grid emissions intensity (gCO₂eq/kWh) for EU countries.

**Like [Carbon Intensity UK](https://api.carbonintensity.org.uk/), but for the EU.**

## Quick Start

```bash
curl "https://grid.deknijf.com/v1/intensity/latest?country=NL"
```

```json
{
  "country": "NL",
  "unit": "gCO2eq/kWh",
  "method": "location-based",
  "data": [
    {
      "timestamp": "2026-03-21T17:00:00Z",
      "intensity": 381.6,
      "generation_mix": {
        "gas_ccgt": 0.26,
        "wind_onshore": 0.09,
        "nuclear": 0.07
      }
    }
  ]
}
```

## Endpoints

| Endpoint | Description |
| --- | --- |
| `GET /v1/countries` | List available countries and bidding zones |
| `GET /v1/intensity?country=NL&start=…&end=…` | Hourly intensity for a time range (max 31 days) |
| `GET /v1/intensity/latest?country=NL` | Most recent data point |

No API key required. No authentication. JSON responses.

## Countries

| Code | Country | Typical gCO₂eq/kWh |
| --- | --- | --- |
| NL | Netherlands | ~400 (gas-heavy) |
| DE | Germany | ~370 (coal + gas) |
| FR | France | ~30 (nuclear) |
| BE | Belgium | ~120 (mixed) |
| DK1 | Denmark West | ~150 (wind + gas) |
| DK2 | Denmark East | ~160 (wind + gas) |

## Data Sources

- **Generation data**: [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/) — real-time output per fuel type
- **Emission factors**: IPCC AR6 lifecycle median gCO₂eq/kWh per generation type
- **Method**: Weighted average — `intensity = Σ(generation_share × emission_factor)` — location-based per GHG Protocol Scope 2 Guidance

## Running Locally

```bash
# Install dependencies
uv sync

# Set ENTSO-E token
echo "ENTSOE_TOKEN=your-token-here" > .env

# Ingest recent data
uv run python -m grid_emissions_api.ingest

# Start the server
uv run uvicorn grid_emissions_api.main:app --port 8000
```

## Docker

```bash
docker compose up -d
```

The API will be available at `http://localhost:8000`. The landing page is served at `/`, API docs at `/docs`.

## Development

```bash
# Run tests
uv run pytest -v

# Backfill historical data
uv run python -m grid_emissions_api.ingest --backfill --start 2020-01-01
```

Pre-commit hooks are configured for linting (ruff), formatting (ruff-format), and type checking (ty).

```bash
pre-commit install
```

## License

MIT
