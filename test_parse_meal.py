import json

import pytest

import project
from project import parse_meal, MealLookupError


def test_unmatched_food_is_reported_not_silently_dropped(monkeypatch):
    monkeypatch.setattr(project, "call_model", lambda text: json.dumps([
        {"food": "unobtainium", "usda_query": "unobtainium", "quantity": 1, "grams_per_item": 100}
    ]))
    monkeypatch.setattr(project, "call_usda", lambda query: {"foods": []})

    meals, unmatched = parse_meal("some unobtainium")

    assert meals == []
    assert unmatched == ["unobtainium"]


def test_matched_food_scales_macros_per_portion(monkeypatch):
    monkeypatch.setattr(project, "call_model", lambda text: json.dumps([
        {"food": "egg", "usda_query": "egg, whole, cooked", "quantity": 2, "grams_per_item": 50}
    ]))
    monkeypatch.setattr(project, "call_usda", lambda query: {"foods": [{
        "fdcId": 1,
        "description": "Egg, whole, cooked",
        "foodNutrients": [
            {"nutrientName": "Energy", "unitName": "KCAL", "value": 150},
            {"nutrientName": "Protein", "unitName": "G", "value": 12},
            {"nutrientName": "Carbohydrate, by difference", "unitName": "G", "value": 1},
            {"nutrientName": "Total lipid (fat)", "unitName": "G", "value": 10},
        ],
    }]})

    meals, unmatched = parse_meal("two eggs")

    assert unmatched == []
    assert len(meals) == 2
    assert meals[0]["grams"] == 50
    assert meals[0]["calories"] == 75.0  # 150 kcal/100g scaled to 50g


def test_propagates_meal_lookup_error_from_call_model(monkeypatch):
    def raise_error(text):
        raise MealLookupError("Could not reach the meal-parsing model. Please try again.")

    monkeypatch.setattr(project, "call_model", raise_error)

    with pytest.raises(MealLookupError):
        parse_meal("anything")


def test_propagates_meal_lookup_error_from_call_usda(monkeypatch):
    monkeypatch.setattr(project, "call_model", lambda text: json.dumps([
        {"food": "egg", "usda_query": "egg", "quantity": 1, "grams_per_item": 50}
    ]))

    def raise_error(query):
        raise MealLookupError("Could not reach the USDA food database. Please try again.")

    monkeypatch.setattr(project, "call_usda", raise_error)

    with pytest.raises(MealLookupError):
        parse_meal("egg")
