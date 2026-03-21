"""Tests for FastAPI endpoints."""

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from grid_emissions_api.database import init_db, upsert_intensity
from grid_emissions_api.emissions import calculate_intensity
from grid_emissions_api.entsoe_client import _parse_generation_xml

SAMPLE_XML = Path(__file__).parent / "sample_entsoe_response.xml"


@pytest.fixture(autouse=True)
def _tmp_db(monkeypatch):
    """Use a temporary database for each test."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test.db")
        monkeypatch.setenv("DATABASE_PATH", db_path)
        # Re-import settings to pick up the new env var
        from grid_emissions_api.config import Settings

        monkeypatch.setattr("grid_emissions_api.database.settings", Settings())
        init_db()
        yield db_path


def _seed_sample_data():
    """Parse sample XML and insert into the test database."""
    gen = _parse_generation_xml(SAMPLE_XML.read_bytes())
    data = calculate_intensity(gen)
    upsert_intensity("NL", data)
    return data


@pytest.fixture
def client():
    from grid_emissions_api.main import app

    return TestClient(app)


def test_list_countries(client):
    resp = client.get("/v1/countries")
    assert resp.status_code == 200
    data = resp.json()
    codes = [c["code"] for c in data["countries"]]
    assert "NL" in codes
    assert "DE" in codes
    assert "FR" in codes
    assert "BE" in codes
    assert "DK1" in codes
    assert "DK2" in codes


def test_list_countries_has_bidding_zones(client):
    resp = client.get("/v1/countries")
    data = resp.json()
    nl = next(c for c in data["countries"] if c["code"] == "NL")
    assert nl["bidding_zone"] == "10YNL----------L"
    assert nl["name"] == "Netherlands"


def test_intensity_invalid_country(client):
    resp = client.get(
        "/v1/intensity",
        params={
            "country": "XX",
            "start": "2026-03-18T23:00:00Z",
            "end": "2026-03-19T02:00:00Z",
        },
    )
    assert resp.status_code == 400
    assert "Unknown country" in resp.json()["detail"]


def test_intensity_end_before_start(client):
    resp = client.get(
        "/v1/intensity",
        params={
            "country": "NL",
            "start": "2026-03-19T02:00:00Z",
            "end": "2026-03-18T23:00:00Z",
        },
    )
    assert resp.status_code == 400
    assert "end must be after start" in resp.json()["detail"]


def test_intensity_max_range_exceeded(client):
    resp = client.get(
        "/v1/intensity",
        params={
            "country": "NL",
            "start": "2026-01-01T00:00:00Z",
            "end": "2026-03-01T00:00:00Z",
        },
    )
    assert resp.status_code == 400
    assert "Max range" in resp.json()["detail"]


def test_intensity_success(client):
    """Test intensity endpoint with data seeded in SQLite."""
    _seed_sample_data()

    resp = client.get(
        "/v1/intensity",
        params={
            "country": "NL",
            "start": "2026-03-18T23:00:00Z",
            "end": "2026-03-19T02:00:00Z",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["country"] == "NL"
    assert data["unit"] == "gCO2eq/kWh"
    assert data["method"] == "location-based"
    assert len(data["data"]) == 3
    assert data["data"][0]["intensity"] > 0
    assert "generation_mix" in data["data"][0]


def test_latest_intensity(client):
    """Test latest endpoint returns only the most recent data point."""
    _seed_sample_data()

    resp = client.get(
        "/v1/intensity/latest",
        params={"country": "NL"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 1


def test_latest_intensity_empty(client):
    """Latest endpoint returns empty data when DB has no rows."""
    resp = client.get(
        "/v1/intensity/latest",
        params={"country": "NL"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"] == []
