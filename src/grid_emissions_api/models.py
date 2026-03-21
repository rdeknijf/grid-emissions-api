from datetime import datetime

from pydantic import BaseModel


# -- Bidding zones for MVP countries --

BIDDING_ZONES: dict[str, dict] = {
    "NL": {
        "name": "Netherlands",
        "zone": "NL",
        "code": "10YNL----------L",
    },
    "DE": {
        "name": "Germany-Luxembourg",
        "zone": "DE-LU",
        "code": "10Y1001A1001A82H",
    },
    "FR": {
        "name": "France",
        "zone": "FR",
        "code": "10YFR-RTE------C",
    },
    "BE": {
        "name": "Belgium",
        "zone": "BE",
        "code": "10YBE----------2",
    },
    "DK1": {
        "name": "Denmark West",
        "zone": "DK1",
        "code": "10YDK-1--------W",
    },
    "DK2": {
        "name": "Denmark East",
        "zone": "DK2",
        "code": "10YDK-2--------M",
    },
}

# -- IPCC AR6 lifecycle emission factors (gCO2eq/kWh) per ENTSO-E PSR code --

EMISSION_FACTORS: dict[str, float] = {
    "B01": 230,  # Biomass
    "B02": 820,  # Hard coal
    "B03": 1000,  # Lignite
    "B04": 490,  # Natural gas (CCGT)
    "B05": 490,  # Natural gas (OCGT)
    "B06": 650,  # Oil
    "B08": 330,  # Waste
    "B09": 38,  # Geothermal
    "B10": 24,  # Hydro pumped storage (generating)
    "B11": 24,  # Hydro run-of-river
    "B12": 24,  # Hydro reservoir
    "B14": 12,  # Nuclear
    "B16": 45,  # Solar
    "B17": 45,  # Solar (thermal)
    "B18": 11,  # Wind onshore
    "B19": 12,  # Wind offshore
    "B20": 500,  # Other (conservative)
}

# Human-readable names for PSR codes
PSR_NAMES: dict[str, str] = {
    "B01": "biomass",
    "B02": "coal",
    "B03": "lignite",
    "B04": "gas_ccgt",
    "B05": "gas_ocgt",
    "B06": "oil",
    "B08": "waste",
    "B09": "geothermal",
    "B10": "hydro_pumped",
    "B11": "hydro_run_of_river",
    "B12": "hydro_reservoir",
    "B14": "nuclear",
    "B16": "solar",
    "B17": "solar_thermal",
    "B18": "wind_onshore",
    "B19": "wind_offshore",
    "B20": "other",
}


# -- API response models --


class GenerationMix(BaseModel):
    """Fraction of total generation per fuel type."""

    model_config = {"extra": "allow"}


class IntensityDataPoint(BaseModel):
    timestamp: datetime
    intensity: float  # gCO2eq/kWh
    generation_mix: dict[str, float]  # fuel_type -> fraction
    is_estimated: bool = False


class IntensityResponse(BaseModel):
    country: str
    bidding_zone: str
    start: datetime
    end: datetime
    granularity: str = "hourly"
    unit: str = "gCO2eq/kWh"
    method: str = "location-based"
    data: list[IntensityDataPoint]
    metadata: dict


class CountryInfo(BaseModel):
    code: str
    name: str
    bidding_zone: str


class CountriesResponse(BaseModel):
    countries: list[CountryInfo]
