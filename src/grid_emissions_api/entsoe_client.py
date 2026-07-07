"""ENTSO-E Transparency Platform API client.

Fetches Actual Generation Per Type (document type A75) and parses the XML
response into structured generation data per hour.
"""

from datetime import datetime

import httpx
from lxml import etree  # type: ignore[import]

from .config import settings
from .models import BIDDING_ZONES

# ENTSO-E XML namespace
NS = {"ns": "urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0"}


def _fmt_ts(dt: datetime) -> str:
    """Format datetime as ENTSO-E expects: YYYYMMDDHHmm."""
    return dt.strftime("%Y%m%d%H%M")


async def fetch_generation(
    country: str,
    start: datetime,
    end: datetime,
) -> dict[datetime, dict[str, float]]:
    """Fetch actual generation per type from ENTSO-E.

    Returns: {timestamp_utc: {psr_code: generation_mw, ...}, ...}
    """
    zone = BIDDING_ZONES[country]

    params = {
        "securityToken": settings.entsoe_token,
        "documentType": "A75",  # Actual Generation Per Type
        "processType": "A16",  # Realised
        "in_Domain": zone["code"],
        "periodStart": _fmt_ts(start),
        "periodEnd": _fmt_ts(end),
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(settings.entsoe_base_url, params=params)
        resp.raise_for_status()

    return _parse_generation_xml(resp.content)


def _parse_generation_xml(xml_bytes: bytes) -> dict[datetime, dict[str, float]]:
    """Parse ENTSO-E A75 XML into {timestamp: {psr_code: mw}}."""
    root = etree.fromstring(xml_bytes)

    # Accumulate running sums and counts per (hour, psr_code) so that
    # sub-hourly points (PT15M/PT30M) can be averaged correctly as sum / n.
    # A running pairwise mean is order-dependent and wrong (it over-weights
    # the later points), so we defer the division until all points are seen.
    sums: dict[datetime, dict[str, float]] = {}
    counts: dict[datetime, dict[str, int]] = {}

    for ts in root.findall(".//ns:TimeSeries", NS):
        # Get the PSR type (fuel type)
        psr_el = ts.find(".//ns:MktPSRType/ns:psrType", NS)
        if psr_el is None:
            continue
        psr_code = psr_el.text

        for period in ts.findall(".//ns:Period", NS):
            start_el = period.find("ns:timeInterval/ns:start", NS)
            resolution_el = period.find("ns:resolution", NS)
            if start_el is None or resolution_el is None:
                continue

            period_start = datetime.fromisoformat(start_el.text.replace("Z", "+00:00"))
            # Parse resolution (PT15M or PT60M)
            resolution_str = resolution_el.text  # e.g. "PT60M" or "PT15M"
            if resolution_str == "PT60M":
                resolution_minutes = 60
            elif resolution_str == "PT15M":
                resolution_minutes = 15
            elif resolution_str == "PT30M":
                resolution_minutes = 30
            else:
                resolution_minutes = 60

            for point in period.findall("ns:Point", NS):
                pos_el = point.find("ns:position", NS)
                qty_el = point.find("ns:quantity", NS)
                if pos_el is None or qty_el is None:
                    continue

                position = int(pos_el.text)
                quantity = float(qty_el.text)

                # Calculate timestamp from period start + position
                from datetime import timedelta

                ts_point = period_start + timedelta(
                    minutes=(position - 1) * resolution_minutes
                )

                # If sub-hourly, round down to hour for aggregation
                if resolution_minutes < 60:
                    ts_point = ts_point.replace(minute=0, second=0, microsecond=0)

                hour_sums = sums.setdefault(ts_point, {})
                hour_counts = counts.setdefault(ts_point, {})
                hour_sums[psr_code] = hour_sums.get(psr_code, 0.0) + quantity
                hour_counts[psr_code] = hour_counts.get(psr_code, 0) + 1

    # Divide accumulated sums by their counts to get the hourly mean.
    return {
        ts_point: {
            psr_code: total / counts[ts_point][psr_code]
            for psr_code, total in hour_sums.items()
        }
        for ts_point, hour_sums in sums.items()
    }
