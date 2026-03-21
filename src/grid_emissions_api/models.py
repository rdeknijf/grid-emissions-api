from datetime import datetime

from pydantic import BaseModel


# -- ENTSO-E bidding zones for all EU-27 countries --

BIDDING_ZONES: dict[str, dict] = {
    # Single-zone countries
    "AT": {"name": "Austria", "zone": "AT", "code": "10YAT-APG------L"},
    "BE": {"name": "Belgium", "zone": "BE", "code": "10YBE----------2"},
    "BG": {"name": "Bulgaria", "zone": "BG", "code": "10YCA-BULGARIA-R"},
    "HR": {"name": "Croatia", "zone": "HR", "code": "10YHR-HEP------M"},
    "CY": {"name": "Cyprus", "zone": "CY", "code": "10YCY-1001A0003J"},
    "CZ": {"name": "Czech Republic", "zone": "CZ", "code": "10YCZ-CEPS-----N"},
    "EE": {"name": "Estonia", "zone": "EE", "code": "10Y1001A1001A39I"},
    "FI": {"name": "Finland", "zone": "FI", "code": "10YFI-1--------U"},
    "FR": {"name": "France", "zone": "FR", "code": "10YFR-RTE------C"},
    "DE": {"name": "Germany-Luxembourg", "zone": "DE-LU", "code": "10Y1001A1001A82H"},
    "GR": {"name": "Greece", "zone": "GR", "code": "10YGR-HTSO-----Y"},
    "HU": {"name": "Hungary", "zone": "HU", "code": "10YHU-MAVIR----U"},
    "IE": {"name": "Ireland", "zone": "IE-SEM", "code": "10Y1001A1001A59C"},
    "IT": {"name": "Italy", "zone": "IT", "code": "10YIT-GRTN-----B"},
    "LV": {"name": "Latvia", "zone": "LV", "code": "10YLV-1001A00074"},
    "LT": {"name": "Lithuania", "zone": "LT", "code": "10YLT-1001A0008Q"},
    "LU": {"name": "Luxembourg", "zone": "LU", "code": "10YLU-CEGEDEL-NQ"},
    "MT": {"name": "Malta", "zone": "MT", "code": "10Y1001A1001A93C"},
    "NL": {"name": "Netherlands", "zone": "NL", "code": "10YNL----------L"},
    "PL": {"name": "Poland", "zone": "PL", "code": "10YPL-AREA-----S"},
    "PT": {"name": "Portugal", "zone": "PT", "code": "10YPT-REN------W"},
    "RO": {"name": "Romania", "zone": "RO", "code": "10YRO-TEL------P"},
    "SK": {"name": "Slovakia", "zone": "SK", "code": "10YSK-SEPS-----K"},
    "SI": {"name": "Slovenia", "zone": "SI", "code": "10YSI-ELES-----O"},
    "ES": {"name": "Spain", "zone": "ES", "code": "10YES-REE------0"},
    # Multi-zone countries
    "DK1": {"name": "Denmark West", "zone": "DK1", "code": "10YDK-1--------W"},
    "DK2": {"name": "Denmark East", "zone": "DK2", "code": "10YDK-2--------M"},
    "SE1": {"name": "Sweden North", "zone": "SE1", "code": "10Y1001A1001A44P"},
    "SE2": {"name": "Sweden Central-North", "zone": "SE2", "code": "10Y1001A1001A45N"},
    "SE3": {"name": "Sweden Central-South", "zone": "SE3", "code": "10Y1001A1001A46L"},
    "SE4": {"name": "Sweden South", "zone": "SE4", "code": "10Y1001A1001A47J"},
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
