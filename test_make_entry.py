from project import make_entry


def test_usda_entry_records_grams():
    entry = make_entry(
        "2026-07-25",
        "banana",
        105,
        1.3,
        27,
        0.4,
        123,
        "Bananas, raw",
        118,
    )

    assert entry["grams"] == 118


def test_manual_entry_has_no_grams():
    entry = make_entry(
        "2026-07-25",
        "banana",
        105,
        1.3,
        27,
        0.4,
        None,
        None,
        None,
    )

    assert entry["grams"] is None
