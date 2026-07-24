from project import scale_macros

per_100g = {"calories": 55.0, "protein": 10.7, "carbs": 2.36, "fat": 0.0}


def test_100_grams_is_unchanged():
    assert scale_macros(per_100g, 100) == per_100g


def test_200_grams_doubles():
    result = scale_macros(per_100g, 200)
    assert result == {"calories": 110.0, "protein": 21.4, "carbs": 4.72, "fat": 0.0}


def test_50_grams_halves():
    result = scale_macros(per_100g, 50)
    assert result == {"calories": 27.5, "protein": 5.35, "carbs": 1.18, "fat": 0.0}


def test_ignores_extra_keys():
    match = {**per_100g, "fdc_id": 747997, "description": "Eggs, Grade A, Large, egg white"}
    result = scale_macros(match, 100)
    assert result == per_100g
