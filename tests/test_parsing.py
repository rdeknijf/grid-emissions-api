"""Tests for ENTSO-E XML parsing."""

from datetime import datetime, timezone
from pathlib import Path

from grid_emissions_api.entsoe_client import _parse_generation_xml

SAMPLE_XML = Path(__file__).parent / "sample_entsoe_response.xml"


def test_parse_returns_three_hours():
    xml = SAMPLE_XML.read_bytes()
    result = _parse_generation_xml(xml)
    assert len(result) == 3


def test_parse_timestamps_are_utc():
    xml = SAMPLE_XML.read_bytes()
    result = _parse_generation_xml(xml)
    for ts in result:
        assert ts.tzinfo is not None


def test_parse_first_hour_has_all_fuel_types():
    xml = SAMPLE_XML.read_bytes()
    result = _parse_generation_xml(xml)
    first_hour = datetime(2026, 3, 18, 23, 0, tzinfo=timezone.utc)
    gen = result[first_hour]
    assert "B18" in gen  # wind onshore
    assert "B04" in gen  # gas CCGT
    assert "B14" in gen  # nuclear
    assert "B16" in gen  # solar


def test_parse_mw_values_correct():
    xml = SAMPLE_XML.read_bytes()
    result = _parse_generation_xml(xml)
    first_hour = datetime(2026, 3, 18, 23, 0, tzinfo=timezone.utc)
    gen = result[first_hour]
    assert gen["B18"] == 3000  # wind
    assert gen["B04"] == 5000  # gas
    assert gen["B14"] == 500  # nuclear
    assert gen["B16"] == 0  # solar (night)


def test_parse_hour_2_values():
    xml = SAMPLE_XML.read_bytes()
    result = _parse_generation_xml(xml)
    hour_2 = datetime(2026, 3, 19, 0, 0, tzinfo=timezone.utc)
    gen = result[hour_2]
    assert gen["B18"] == 3200
    assert gen["B04"] == 4800
    assert gen["B14"] == 500
    assert gen["B16"] == 200


def _subhourly_xml(quantities: list[float]) -> bytes:
    """Build a minimal A75 doc with one PT15M period of the given points."""
    points = "".join(
        f"<Point><position>{i + 1}</position>"
        f"<quantity>{q}</quantity></Point>"
        for i, q in enumerate(quantities)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<GL_MarketDocument '
        'xmlns="urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0">'
        "<TimeSeries>"
        "<MktPSRType><psrType>B04</psrType></MktPSRType>"
        "<Period>"
        "<timeInterval><start>2026-03-19T00:00Z</start>"
        "<end>2026-03-19T01:00Z</end></timeInterval>"
        "<resolution>PT15M</resolution>"
        f"{points}"
        "</Period>"
        "</TimeSeries>"
        "</GL_MarketDocument>"
    ).encode()


def test_subhourly_points_averaged_by_mean():
    # Four PT15M points collapse into one hour; the value must be the
    # arithmetic mean (sum / n), not an order-dependent running pairwise mean.
    xml = _subhourly_xml([100, 200, 300, 400])
    result = _parse_generation_xml(xml)
    hour = datetime(2026, 3, 19, 0, 0, tzinfo=timezone.utc)
    assert result[hour]["B04"] == 250  # mean, not 312.5 (pairwise)
