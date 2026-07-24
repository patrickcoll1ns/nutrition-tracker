import json
from project import parse_usda_response


def test_parses_real_fixture():
    with open("usda_egg_response.json") as f:
        data = json.load(f)
    result = parse_usda_response(data)
    assert result == [{
        "fdc_id": 747997,
        "description": "Eggs, Grade A, Large, egg white",
        "calories": 55.0,
        "protein": 10.7,
        "carbs": 2.36,
        "fat": 0.0,
    }]


def test_no_foods_key_returns_empty():
    assert parse_usda_response({}) == []


def test_empty_foods_list_returns_empty():
    assert parse_usda_response({"foods": []}) == []


def test_drops_food_missing_a_nutrient():
    data = {"foods": [{
        "fdcId": 1,
        "description": "incomplete food",
        "foodNutrients": [
            {"nutrientName": "Energy", "unitName": "KCAL", "value": 100},
            {"nutrientName": "Protein", "unitName": "G", "value": 5},
            # carbs and fat missing
        ],
    }]}
    assert parse_usda_response(data) == []


def test_does_not_confuse_kj_energy_with_kcal():
    data = {"foods": [{
        "fdcId": 2,
        "description": "kj trap",
        "foodNutrients": [
            {"nutrientName": "Energy", "unitName": "kJ", "value": 999},
            {"nutrientName": "Energy", "unitName": "KCAL", "value": 50},
            {"nutrientName": "Protein", "unitName": "G", "value": 1},
            {"nutrientName": "Carbohydrate, by difference", "unitName": "G", "value": 1},
            {"nutrientName": "Total lipid (fat)", "unitName": "G", "value": 1},
        ],
    }]}
    result = parse_usda_response(data)
    assert result[0]["calories"] == 50
