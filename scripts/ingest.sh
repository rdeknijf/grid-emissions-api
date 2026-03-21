#!/bin/sh
# Run hourly ingestion inside the running container.
# Install via crontab: 5 * * * * /path/to/scripts/ingest.sh >> /var/log/grid-emissions-ingest.log 2>&1
docker exec grid-emissions uv run python -m grid_emissions_api.ingest --hours 3
