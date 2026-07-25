from project import make_entry


def test_usda_entry_records_grams():
    entry = make_entry(
        "2026-07-25",
        "banana",
        calories=105,
        protein=1.3,
        carbs=27,
        fat=0.4,
        usda_id=123,
        usda_description="Bananas, raw",
        grams=118,
    )

    assert entry["grams"] == 118


def test_manual_entry_has_no_grams():
    entry = make_entry(
        "2026-07-25",
        "banana",
        calories=105,
        protein=1.3,
        carbs=27,
        fat=0.4,
        usda_id=None,
        usda_description=None,
        grams=None,
    )

    assert entry["grams"] is None
