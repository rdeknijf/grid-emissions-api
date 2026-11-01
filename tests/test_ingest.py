"""Tests for ingest error logging."""

import httpx

from grid_emissions_api.ingest import _describe_error


def test_http_error_log_omits_the_token():
    url = "https://web-api.tp.entsoe.eu/api?securityToken=secret-token&in_Domain=X"
    request = httpx.Request("GET", url)
    response = httpx.Response(599, request=request)
    error = httpx.HTTPStatusError(
        "Server error for url " + url, request=request, response=response
    )
    message = _describe_error(error)
    assert "secret-token" not in message
    assert message == "HTTPStatusError: HTTP 599"


def test_empty_error_message_still_names_the_error():
    assert _describe_error(httpx.ReadTimeout("")) == "ReadTimeout"
