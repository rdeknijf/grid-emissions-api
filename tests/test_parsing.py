"""Tests for ENTSO-E XML parsing."""

from datetime import UTC, datetime
from pathlib import Path

from grid_emissions_api.emissions import calculate_intensity
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
    first_hour = datetime(2026, 3, 18, 23, 0, tzinfo=UTC)
    gen = result[first_hour]
    assert "B18" in gen  # wind onshore
    assert "B04" in gen  # gas CCGT
    assert "B14" in gen  # nuclear
    assert "B16" in gen  # solar


def test_parse_mw_values_correct():
    xml = SAMPLE_XML.read_bytes()
    result = _parse_generation_xml(xml)
    first_hour = datetime(2026, 3, 18, 23, 0, tzinfo=UTC)
    gen = result[first_hour]
    assert gen["B18"] == 3000  # wind
    assert gen["B04"] == 5000  # gas
    assert gen["B14"] == 500  # nuclear
    assert gen["B16"] == 0  # solar (night)


def test_parse_hour_2_values():
    xml = SAMPLE_XML.read_bytes()
    result = _parse_generation_xml(xml)
    hour_2 = datetime(2026, 3, 19, 0, 0, tzinfo=UTC)
    gen = result[hour_2]
    assert gen["B18"] == 3200
    assert gen["B04"] == 4800
    assert gen["B14"] == 500
    assert gen["B16"] == 200


def _subhourly_xml(quantities: list[float]) -> bytes:
    """Build a minimal A75 doc with one PT15M period of the given points."""
    points = "".join(
        f"<Point><position>{i + 1}</position><quantity>{q}</quantity></Point>"
        for i, q in enumerate(quantities)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<GL_MarketDocument "
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


def test_external_entity_is_not_resolved():
    # An XXE payload: the &xxe; entity must NOT be expanded into file contents.
    # With the hardened parser this either raises or leaves the entity unresolved
    # — either way, /etc/passwd never reaches the parsed tree.
    xxe = (
        b'<?xml version="1.0"?>'
        b'<!DOCTYPE r [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
        b"<GL_MarketDocument "
        b'xmlns="urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0">'
        b"<TimeSeries><MktPSRType><psrType>&xxe;</psrType></MktPSRType>"
        b"</TimeSeries></GL_MarketDocument>"
    )
    try:
        result = _parse_generation_xml(xxe)
    except Exception:
        return  # parser rejected the DTD/entity outright — acceptable
    # If it parsed, no PSR code carried the file contents.
    for gen in result.values():
        assert not any("root:" in code for code in gen)


def test_subhourly_points_averaged_by_mean():
    # Four PT15M points collapse into one hour; the value must be the
    # arithmetic mean (sum / n), not an order-dependent running pairwise mean.
    xml = _subhourly_xml([100, 200, 300, 400])
    result = _parse_generation_xml(xml)
    hour = datetime(2026, 3, 19, 0, 0, tzinfo=UTC)
    assert result[hour]["B04"] == 250  # mean, not 312.5 (pairwise)


# A real A75 response for NL, 2026-11-01 05:00-08:00 UTC, as the hourly ingest
# requests it. It has the three traits the parser must handle: curveType A03
# (a point only where the value changes), a consumption series per fuel type
# (outBiddingZone_Domain), and data that ends at 07:15, one quarter into the
# last hour.
NL_A03_XML = Path(__file__).parent / "entsoe_a75_nl_2026-11-01.xml"


def _series(psr: str, points: dict[int, float], *, domain: str = "in") -> str:
    point_xml = "".join(
        f"<Point><position>{pos}</position><quantity>{q}</quantity></Point>"
        for pos, q in points.items()
    )
    return (
        "<TimeSeries>"
        f'<{domain}BiddingZone_Domain.mRID codingScheme="A01">10YNL----------L'
        f"</{domain}BiddingZone_Domain.mRID>"
        "<curveType>A03</curveType>"
        f"<MktPSRType><psrType>{psr}</psrType></MktPSRType>"
        "<Period>"
        "<timeInterval><start>2026-03-19T00:00Z</start>"
        "<end>2026-03-19T02:00Z</end></timeInterval>"
        "<resolution>PT15M</resolution>"
        f"{point_xml}"
        "</Period>"
        "</TimeSeries>"
    )


def _doc(*series: str) -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<GL_MarketDocument "
        'xmlns="urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0">'
        f"{''.join(series)}"
        "</GL_MarketDocument>"
    ).encode()


def test_a03_value_holds_until_next_point():
    # A03: positions 2-3 repeat 100, positions 5-8 repeat 300. Hour 0 is
    # (100 + 100 + 100 + 300) / 4, not the mean of the two listed points.
    result = _parse_generation_xml(_doc(_series("B04", {1: 100, 4: 300})))
    assert result[datetime(2026, 3, 19, 0, 0, tzinfo=UTC)]["B04"] == 150
    assert result[datetime(2026, 3, 19, 1, 0, tzinfo=UTC)]["B04"] == 300


def test_a03_single_point_fills_the_whole_period():
    # A flat series (constant nuclear) arrives as one point; it must count in
    # every hour, or the hour's mix silently drops that fuel.
    result = _parse_generation_xml(
        _doc(_series("B04", {1: 100, 3: 200}), _series("B14", {1: 480}))
    )
    for hour in (0, 1):
        assert result[datetime(2026, 3, 19, hour, 0, tzinfo=UTC)]["B14"] == 480


def test_consumption_series_is_ignored():
    result = _parse_generation_xml(
        _doc(_series("B04", {1: 6000}), _series("B04", {1: 20}, domain="out"))
    )
    assert result[datetime(2026, 3, 19, 0, 0, tzinfo=UTC)]["B04"] == 6000


def test_hour_missing_a_fuel_type_is_dropped():
    # B14 ends after hour 0 (a series that is still filling in upstream), so
    # hour 1 would carry a partial mix and must not be returned.
    result = _parse_generation_xml(
        _doc(
            _series("B04", {1: 100, 5: 200}),
            _series("B14", {1: 480}).replace("02:00Z</end>", "01:00Z</end>"),
        )
    )
    assert list(result) == [datetime(2026, 3, 19, 0, 0, tzinfo=UTC)]


def test_series_that_starts_late_keeps_the_earlier_hours():
    # Pumped storage (B10) generates only from 01:00; hour 0 is still complete.
    result = _parse_generation_xml(
        _doc(
            _series("B04", {1: 100}),
            _series("B10", {1: 50}).replace("00:00Z</start>", "01:00Z</start>"),
        )
    )
    assert result[datetime(2026, 3, 19, 0, 0, tzinfo=UTC)] == {"B04": 100}
    assert result[datetime(2026, 3, 19, 1, 0, tzinfo=UTC)] == {"B04": 100, "B10": 50}


def test_series_that_stops_early_keeps_the_later_hours():
    # Pumped storage (B10) stops generating at 00:30, long before the other
    # series end at 03:00. That is a fuel type that is off, not lag.
    result = _parse_generation_xml(
        _doc(
            _series("B04", {1: 100}).replace("02:00Z</end>", "03:00Z</end>"),
            _series("B10", {1: 50}).replace("02:00Z</end>", "00:30Z</end>"),
        )
    )
    assert sorted(result) == [
        datetime(2026, 3, 19, hour, 0, tzinfo=UTC) for hour in (0, 1, 2)
    ]


def test_real_nl_response_drops_the_partial_last_hour():
    result = _parse_generation_xml(NL_A03_XML.read_bytes())
    assert sorted(result) == [
        datetime(2026, 11, 1, 5, 0, tzinfo=UTC),
        datetime(2026, 11, 1, 6, 0, tzinfo=UTC),
    ]


def test_real_nl_response_values():
    result = _parse_generation_xml(NL_A03_XML.read_bytes())
    hour = result[datetime(2026, 11, 1, 5, 0, tzinfo=UTC)]
    assert len(hour) == 10  # every fuel type in the document
    # Gas generation is ~5.7 GW. Averaged with its ~20 MW consumption series
    # (the old behaviour) it read as ~2.8 GW.
    assert round(hour["B04"], 1) == 5673.3
    # Nuclear is nearly flat, so A03 lists few points; filled forward it is
    # the full ~480 MW for the hour, not a mean over the listed points only.
    assert round(hour["B14"], 1) == 480.6


def test_real_nl_response_intensity():
    # 447.8 and 443.7 gCO2eq/kWh. The old parser returned 436.8 and 426.9,
    # plus a 426.7 for 07:00 built from a single quarter.
    data = calculate_intensity(_parse_generation_xml(NL_A03_XML.read_bytes()))
    assert [p.intensity for p in data] == [447.8, 443.7]
