import json

from project import parse_response
import pytest


def test_single_food():
    raw = (
        '[{"food": "chicken", "usda_query": "chicken breast, grilled", '
        '"quantity": 1, "grams_per_item": 150}]'
    )
    result = parse_response(raw)
    assert result == [{
        "food": "chicken",
        "usda_query": "chicken breast, grilled",
        "quantity": 1,
        "grams_per_item": 150,
    }]


def test_multi_food():
    raw = (
        '[{"food": "chicken", "usda_query": "chicken breast, grilled", '
        '"quantity": 1, "grams_per_item": 150}, '
        '{"food": "rice", "usda_query": "rice, cooked", '
        '"quantity": 1, "grams_per_item": 200}]'
    )
    result = parse_response(raw)
    assert len(result) == 2
    assert result[0]["food"] == "chicken"
    assert result[1]["food"] == "rice"


def test_strips_code_fences():
    raw = (
        '```json\n[{"food": "egg", "usda_query": "egg, whole, cooked", '
        '"quantity": 2, "grams_per_item": 50}]\n```'
    )
    result = parse_response(raw)
    assert result == [{
        "food": "egg",
        "usda_query": "egg, whole, cooked",
        "quantity": 2,
        "grams_per_item": 50,
    }]


def test_drops_malformed_item():
    raw = (
        '[{"food": "chicken", "usda_query": "chicken breast, grilled", '
        '"quantity": 1, "grams_per_item": 150}, {"food": "rice"}]'
    )
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


@pytest.mark.parametrize("item", [
    {
        "food": "",
        "usda_query": "banana, raw",
        "quantity": 1,
        "grams_per_item": 118,
    },
    {
        "food": "banana",
        "usda_query": "",
        "quantity": 1,
        "grams_per_item": 118,
    },
    {
        "food": "banana",
        "usda_query": "banana, raw",
        "quantity": 0,
        "grams_per_item": 118,
    },
    {
        "food": "banana",
        "usda_query": "banana, raw",
        "quantity": -1,
        "grams_per_item": 118,
    },
    {
        "food": "banana",
        "usda_query": "banana, raw",
        "quantity": 1.5,
        "grams_per_item": 118,
    },
    {
        "food": "banana",
        "usda_query": "banana, raw",
        "quantity": True,
        "grams_per_item": 118,
    },
    {
        "food": "banana",
        "usda_query": "banana, raw",
        "quantity": 1,
        "grams_per_item": 0,
    },
    {
        "food": "banana",
        "usda_query": "banana, raw",
        "quantity": 1,
        "grams_per_item": -10,
    },
    {
        "food": "banana",
        "usda_query": "banana, raw",
        "quantity": 1,
        "grams_per_item": True,
    },
])
def test_drops_invalid_values(item):
    assert parse_response(json.dumps([item])) == []
