from project import expand_food_item


def test_expands_multiple_items():
    item = {
        "food": "egg",
        "usda_query": "egg, whole, cooked",
        "quantity": 2,
        "grams_per_item": 50,
    }

    assert expand_food_item(item) == [
        {
            "food": "egg",
            "usda_query": "egg, whole, cooked",
            "grams": 50,
        },
        {
            "food": "egg",
            "usda_query": "egg, whole, cooked",
            "grams": 50,
        },
    ]


def test_single_item_creates_one_portion():
    item = {
        "food": "banana",
        "usda_query": "banana, raw",
        "quantity": 1,
        "grams_per_item": 118,
    }

    assert expand_food_item(item) == [{
        "food": "banana",
        "usda_query": "banana, raw",
        "grams": 118,
    }]


def test_does_not_mutate_original():
    item = {
        "food": "egg",
        "usda_query": "egg, whole, cooked",
        "quantity": 2,
        "grams_per_item": 50,
    }

    expand_food_item(item)

    assert item["quantity"] == 2
    assert item["grams_per_item"] == 50
    assert "grams" not in item
