import requests
import pytest

from project import call_usda, MealLookupError


def test_wraps_http_errors_without_leaking_api_key(monkeypatch):
    monkeypatch.setenv("USDA_API_KEY", "SUPER-SECRET-KEY")

    class FakeResponse:
        def raise_for_status(self):
            raise requests.exceptions.HTTPError(
                "403 Client Error: Forbidden for url: "
                "https://api.nal.usda.gov/fdc/v1/foods/search?api_key=SUPER-SECRET-KEY"
            )

    monkeypatch.setattr("project.requests.post", lambda *a, **k: FakeResponse())

    with pytest.raises(MealLookupError) as exc_info:
        call_usda("egg")

    assert "SUPER-SECRET-KEY" not in str(exc_info.value)


def test_wraps_connection_errors(monkeypatch):
    monkeypatch.setenv("USDA_API_KEY", "fake-key")

    def raise_connection_error(*args, **kwargs):
        raise requests.exceptions.ConnectionError("connection refused")

    monkeypatch.setattr("project.requests.post", raise_connection_error)

    with pytest.raises(MealLookupError):
        call_usda("egg")


def test_wraps_timeouts(monkeypatch):
    monkeypatch.setenv("USDA_API_KEY", "fake-key")

    def raise_timeout(*args, **kwargs):
        raise requests.exceptions.Timeout("timed out")

    monkeypatch.setattr("project.requests.post", raise_timeout)

    with pytest.raises(MealLookupError):
        call_usda("egg")
