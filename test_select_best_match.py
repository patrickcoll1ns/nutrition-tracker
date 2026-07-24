from project import select_best_match


def test_returns_first_of_multiple():
    foods = [
        {"fdc_id": 1, "description": "first"},
        {"fdc_id": 2, "description": "second"},
    ]
    assert select_best_match(foods) == {"fdc_id": 1, "description": "first"}


def test_single_item_list():
    foods = [{"fdc_id": 1, "description": "only one"}]
    assert select_best_match(foods) == {"fdc_id": 1, "description": "only one"}


def test_empty_list_returns_none():
    assert select_best_match([]) is None
