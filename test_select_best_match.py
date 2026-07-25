from project import select_best_match


def test_returns_first_of_multiple():
    foods = [
        {"fdc_id": 1, "description": "first"},
        {"fdc_id": 2, "description": "second"},
    ]
    assert select_best_match(foods, "unknown") == {
        "fdc_id": 1,
        "description": "first",
    }


def test_single_item_list():
    foods = [{"fdc_id": 1, "description": "only one"}]
    assert select_best_match(foods, "only one") == {
        "fdc_id": 1,
        "description": "only one",
    }


def test_empty_list_returns_none():
    assert select_best_match([], "banana") is None


def test_plain_banana_prefers_raw_over_processed_results():
    foods = [
        {"fdc_id": 1, "description": "Bananas, dehydrated, or banana powder"},
        {"fdc_id": 2, "description": "Banana, baked"},
        {"fdc_id": 3, "description": "Banana, raw"},
    ]

    assert select_best_match(foods, "banana") == {
        "fdc_id": 3,
        "description": "Banana, raw",
    }


def test_explicit_preparation_is_respected():
    foods = [
        {"fdc_id": 1, "description": "Banana, raw"},
        {"fdc_id": 2, "description": "Banana, baked"},
    ]

    assert select_best_match(foods, "baked banana") == {
        "fdc_id": 2,
        "description": "Banana, baked",
    }
