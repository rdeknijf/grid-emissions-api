"""Grid Emissions Intensity API.

Serves hourly gCO2eq/kWh electricity grid emissions intensity
for EU countries, sourced from ENTSO-E Transparency Platform.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse

from .database import init_db, query_intensity, query_latest
from .models import (
    BIDDING_ZONES,
    CountriesResponse,
    CountryInfo,
    IntensityResponse,
)

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="EU Grid Emissions Intensity API",
    description=(
        "Hourly gCO2eq/kWh electricity grid emissions intensity "
        "for EU countries, sourced from ENTSO-E Transparency Platform."
    ),
    version="0.2.0",
    lifespan=lifespan,
)


@app.get("/", include_in_schema=False)
async def landing_page():
    return FileResponse(
        STATIC_DIR / "index.html",
        headers={"Cache-Control": "public, max-age=3600"},
    )


def _validate_country(country: str) -> str:
    """Validate and normalise country code."""
    country = country.upper()
    if country not in BIDDING_ZONES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown country: {country}. Available: {list(BIDDING_ZONES.keys())}",
        )
    return country


@app.middleware("http")
async def cache_headers(request: Request, call_next):
    response: Response = await call_next(request)
    path = request.url.path
    if path == "/v1/countries":
        response.headers["Cache-Control"] = "public, max-age=86400"
    elif path == "/v1/intensity/latest":
        response.headers["Cache-Control"] = "public, max-age=300, s-maxage=900"
    elif path == "/v1/intensity":
        response.headers["Cache-Control"] = "public, max-age=3600"
    return response


@app.get("/v1/countries", response_model=CountriesResponse)
async def list_countries():
    """List available countries and their bidding zones."""
    return CountriesResponse(
        countries=[
            CountryInfo(code=code, name=z["name"], bidding_zone=z["code"])
            for code, z in BIDDING_ZONES.items()
        ]
    )


@app.get("/v1/intensity", response_model=IntensityResponse)
async def get_intensity(
    country: str = Query(
        ..., description="ISO country code or bidding zone (e.g. NL, DE, FR, SE1)"
    ),
    start: datetime = Query(..., description="Start time (UTC, ISO 8601)"),
    end: datetime = Query(..., description="End time (UTC, ISO 8601)"),
):
    """Get hourly emissions intensity for a country and time range."""
    country = _validate_country(country)
    zone = BIDDING_ZONES[country]

    if end <= start:
        raise HTTPException(status_code=400, detail="end must be after start")
    if (end - start).days > 31:
        raise HTTPException(status_code=400, detail="Max range is 31 days")

    data = query_intensity(country, start, end)

    return IntensityResponse(
        country=country,
        bidding_zone=zone["code"],
        start=start,
        end=end,
        data=data,
        metadata={
            "data_source": "ENTSO-E Transparency Platform",
            "emission_factors": "IPCC AR6 lifecycle median",
        },
    )


@app.get("/v1/intensity/latest", response_model=IntensityResponse)
async def get_latest_intensity(
    country: str = Query(
        ..., description="ISO country code or bidding zone (e.g. NL, DE, FR, SE1)"
    ),
):
    """Get the most recent emissions intensity for a country."""
    country = _validate_country(country)
    zone = BIDDING_ZONES[country]

    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    data = query_latest(country)
    start = data[0].timestamp if data else now - timedelta(hours=24)

    return IntensityResponse(
        country=country,
        bidding_zone=zone["code"],
        start=start,
        end=now,
        data=data,
        metadata={
            "data_source": "ENTSO-E Transparency Platform",
            "emission_factors": "IPCC AR6 lifecycle median",
        },
    )
