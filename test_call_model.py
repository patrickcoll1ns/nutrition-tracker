import anthropic
import httpx
import pytest

from project import call_model, MealLookupError


def test_wraps_anthropic_api_errors(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")

    class FakeMessages:
        def create(self, **kwargs):
            request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
            raise anthropic.APIConnectionError(request=request)

    class FakeClient:
        messages = FakeMessages()

    monkeypatch.setattr(anthropic, "Anthropic", lambda api_key: FakeClient())

    with pytest.raises(MealLookupError):
        call_model("two eggs and toast")


def test_wraps_response_with_no_text_block(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")

    class FakeResponse:
        content = []  # no text block at all

    class FakeMessages:
        def create(self, **kwargs):
            return FakeResponse()

    class FakeClient:
        messages = FakeMessages()

    monkeypatch.setattr(anthropic, "Anthropic", lambda api_key: FakeClient())

    with pytest.raises(MealLookupError):
        call_model("two eggs and toast")
