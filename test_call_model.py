import anthropic
import httpx
import pytest

import project
from project import call_model, analyze_nutrition_trends, MealLookupError


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


def test_analyze_nutrition_trends_uses_daily_totals(monkeypatch):
    captured = {}

    class TextBlock:
        type = "text"
        text = "Calories were steady across your logged days."

    class FakeResponse:
        content = [TextBlock()]

    class FakeMessages:
        def create(self, **kwargs):
            captured.update(kwargs)
            return FakeResponse()

    class FakeClient:
        messages = FakeMessages()

    monkeypatch.setattr(project, "get_client", lambda: FakeClient())
    daily_totals = [
        {
            "date": "2026-07-25",
            "calories": 2000,
            "protein": 150,
            "carbs": 200,
            "fat": 67,
        }
    ]

    result = analyze_nutrition_trends(daily_totals)

    assert result == "Calories were steady across your logged days."
    assert "2026-07-25" in captured["messages"][0]["content"]


def test_analyze_nutrition_trends_handles_empty_period():
    assert "Log at least one day" in analyze_nutrition_trends([])
