"""ENTSO-E Transparency Platform API client.

Fetches Actual Generation Per Type (document type A75) and parses the XML
response into structured generation data per hour.
"""

from datetime import datetime, timedelta

import httpx
from lxml import etree

from .config import settings
from .models import BIDDING_ZONES

# ENTSO-E XML namespace
NS = {"ns": "urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0"}

# Hardened parser: never resolve entities, load DTDs, or hit the network while
# parsing untrusted upstream XML. Defends against XXE / entity-expansion even
# though the source is currently trusted — cheap defence in depth.
_SAFE_PARSER = etree.XMLParser(
    resolve_entities=False,
    no_network=True,
    load_dtd=False,
    dtd_validation=False,
    huge_tree=False,
)


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


_RESOLUTION_MINUTES = {"PT15M": 15, "PT30M": 30, "PT60M": 60}


# How far a generation series may end behind the latest one and still count
# as lagging (its newest data is not published yet) rather than stopped. DE on
# 2026-11-01 had seven fuel types 75 minutes behind the other nine; a 1-hour
# limit took them as stopped and stored a 7-fuel mix at about 700 gCO2eq/kWh.
# In full-day responses (AT, ES, PT, SK, 2026-10-30) no series stopped early:
# a fuel type that is off reports zeros to the end. The limit stays below the
# hourly ingest window (8 hours), so if a series ever does stop, the hours
# after it are delayed by at most 3 hours, not lost.
_MAX_SERIES_LAG = timedelta(hours=3)


def _period_points(period: etree._Element, curve_type: str) -> dict[int, float]:
    """Return {position: quantity} for one Period, expanded per curve type.

    A01 (sequential fixed size blocks) lists every position. A03 (variable
    sized blocks) lists a point only where the value changes: the value holds
    until the next listed position or the end of the period. ENTSO-E sends A75
    as A03, so a constant series (flat nuclear, zero solar at night) comes as
    a single point and must be filled forward to the period end.
    """
    points: dict[int, float] = {}
    for point in period.findall("ns:Point", NS):
        pos_el = point.find("ns:position", NS)
        qty_el = point.find("ns:quantity", NS)
        if pos_el is None or pos_el.text is None:
            continue
        if qty_el is None or qty_el.text is None:
            continue
        points[int(pos_el.text)] = float(qty_el.text)

    if curve_type != "A03" or not points:
        return points

    start_el = period.find("ns:timeInterval/ns:start", NS)
    end_el = period.find("ns:timeInterval/ns:end", NS)
    resolution_el = period.find("ns:resolution", NS)
    if (
        start_el is None
        or start_el.text is None
        or end_el is None
        or end_el.text is None
        or resolution_el is None
        or resolution_el.text not in _RESOLUTION_MINUTES
    ):
        return points
    span = datetime.fromisoformat(end_el.text) - datetime.fromisoformat(start_el.text)
    n_positions = int(span / timedelta(minutes=_RESOLUTION_MINUTES[resolution_el.text]))

    filled: dict[int, float] = {}
    value: float | None = None
    for position in range(1, n_positions + 1):
        value = points.get(position, value)
        if value is not None:
            filled[position] = value
    return filled


def _parse_generation_xml(xml_bytes: bytes) -> dict[datetime, dict[str, float]]:
    """Parse ENTSO-E A75 XML into {timestamp: {psr_code: mw}}.

    Only generation series count. A75 also carries consumption series (pumped
    storage pumping, and per fuel type for some zones), marked by
    outBiddingZone_Domain instead of inBiddingZone_Domain; those are skipped.

    Upstream fills the most recent hour in gradually: one quarter of it, or
    only some fuel types. A partial mix gives a wrong intensity, so hours that
    end after the earliest lagging series end are dropped. The next ingest run
    picks such an hour up once every series reaches past it. A series counts
    as lagging when it ends at most _MAX_SERIES_LAG before the latest series
    end; only a series further behind is taken as stopped. A series that
    starts late (pumped storage that generates only part of the day) never
    cuts the window.
    """
    root = etree.fromstring(xml_bytes, parser=_SAFE_PARSER)

    # Accumulate running sums and counts per (hour, psr_code) so that
    # sub-hourly points (PT15M/PT30M) can be averaged correctly as sum / n.
    # A running pairwise mean is order-dependent and wrong (it over-weights
    # the later points), so we defer the division until all points are seen.
    sums: dict[datetime, dict[str, float]] = {}
    counts: dict[datetime, dict[str, int]] = {}
    # The end of data of each generation series (see docstring).
    series_ends: list[datetime] = []

    for ts in root.findall(".//ns:TimeSeries", NS):
        if ts.find("ns:outBiddingZone_Domain.mRID", NS) is not None:
            continue  # consumption, not generation

        # Get the PSR type (fuel type)
        psr_el = ts.find(".//ns:MktPSRType/ns:psrType", NS)
        if psr_el is None or psr_el.text is None:
            continue
        psr_code = psr_el.text
        curve_el = ts.find("ns:curveType", NS)
        # No curveType element means A01 (ENTSO-E curve type guide).
        curve_type = curve_el.text if curve_el is not None and curve_el.text else "A01"

        series_end: datetime | None = None
        for period in ts.findall(".//ns:Period", NS):
            start_el = period.find("ns:timeInterval/ns:start", NS)
            resolution_el = period.find("ns:resolution", NS)
            if start_el is None or start_el.text is None or resolution_el is None:
                continue

            period_start = datetime.fromisoformat(start_el.text)
            resolution_minutes = _RESOLUTION_MINUTES.get(resolution_el.text or "", 60)

            points = _period_points(period, curve_type)
            end_el = period.find("ns:timeInterval/ns:end", NS)
            if points and end_el is not None and end_el.text is not None:
                period_end = datetime.fromisoformat(end_el.text)
                series_end = max(series_end or period_end, period_end)

            for position, quantity in points.items():
                ts_point = period_start + timedelta(
                    minutes=(position - 1) * resolution_minutes
                )
                # Round down to the hour for aggregation.
                ts_point = ts_point.replace(minute=0, second=0, microsecond=0)

                hour_sums = sums.setdefault(ts_point, {})
                hour_counts = counts.setdefault(ts_point, {})
                hour_sums[psr_code] = hour_sums.get(psr_code, 0.0) + quantity
                hour_counts[psr_code] = hour_counts.get(psr_code, 0) + 1

        if series_end is not None:
            series_ends.append(series_end)

    data_end: datetime | None = None
    if series_ends:
        latest = max(series_ends)
        data_end = min(e for e in series_ends if e >= latest - _MAX_SERIES_LAG)

    # Divide accumulated sums by their counts to get the hourly mean, and
    # keep only hours that end at or before data_end.
    return {
        ts_point: {
            psr_code: total / counts[ts_point][psr_code]
            for psr_code, total in hour_sums.items()
        }
        for ts_point, hour_sums in sums.items()
        if data_end is None or ts_point + timedelta(hours=1) <= data_end
    }
