"""Calculate emissions intensity from generation mix data."""

from collections.abc import Mapping
from datetime import datetime

from .models import EMISSION_FACTORS, PSR_NAMES, IntensityDataPoint


def calculate_intensity(
    generation: Mapping[datetime, Mapping[str, float]],
) -> list[IntensityDataPoint]:
    """Calculate gCO2eq/kWh for each hour from generation data.

    Args:
        generation: {timestamp: {psr_code: generation_mw, ...}}

    Returns:
        List of IntensityDataPoint sorted by timestamp.
    """
    results: list[IntensityDataPoint] = []

    for timestamp in sorted(generation):
        gen_mix = generation[timestamp]

        total_mw = 0.0
        weighted_emissions = 0.0
        mix_fractions: dict[str, float] = {}

        for psr_code, mw in gen_mix.items():
            if mw <= 0:
                continue
            factor = EMISSION_FACTORS.get(psr_code, 500)  # conservative default
            total_mw += mw
            weighted_emissions += mw * factor

        if total_mw == 0:
            continue

        intensity = weighted_emissions / total_mw

        # Calculate generation mix fractions
        for psr_code, mw in gen_mix.items():
            if mw <= 0:
                continue
            name = PSR_NAMES.get(psr_code, psr_code.lower())
            mix_fractions[name] = round(mw / total_mw, 4)

        results.append(
            IntensityDataPoint(
                timestamp=timestamp,
                intensity=round(intensity, 1),
                generation_mix=mix_fractions,
            )
        )

    return results
