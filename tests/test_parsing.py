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
