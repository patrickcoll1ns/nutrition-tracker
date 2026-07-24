from project import parse_response
import pytest


def test_single_food():
    raw = '[{"food": "chicken", "grams": 150}]'
    result = parse_response(raw)
    assert result == [{"food": "chicken", "grams": 150}]


def test_multi_food():
    raw = '[{"food": "chicken", "grams": 150}, {"food": "rice", "grams": 200}]'
    result = parse_response(raw)
    assert len(result) == 2
    assert result[0]["food"] == "chicken"
    assert result[1]["food"] == "rice"


def test_strips_code_fences():
    raw = '```json\n[{"food": "egg", "grams": 50}]\n```'
    result = parse_response(raw)
    assert result == [{"food": "egg", "grams": 50}]


def test_drops_malformed_item():
    # first item complete; second is missing grams entirely
    raw = '[{"food": "chicken", "grams": 150}, {"food": "rice"}]'
    result = parse_response(raw)
    assert len(result) == 1
    assert result[0]["food"] == "chicken"


@pytest.mark.parametrize("raw", [
    "sorry, I can't help with that",     # not JSON
    "",                                  # empty string
    '{"food": "egg", "calories": 70}',   # valid JSON but an object, not a list
    "42",                                # valid JSON but not a list
])
def test_bad_input_returns_empty(raw):
    assert parse_response(raw) == []