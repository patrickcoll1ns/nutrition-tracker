import db

entry = {"date": "7/11/2026",
         "food": "chicken",
         "calories": 190,
         "protein": 30.0,
         "carbs": 4.5,
         "fat": 0.3,
         "usda_id": None,
         "usda_description": None,
         "grams": None}


def test_load_and_save(tmp_path):
    db.init_db(tmp_path / "entries.db")
    db.save_entry(entry)

    assert db.load_entries() == [entry]


def test_new_database_is_empty():
    db.init_db(":memory:")

    assert db.load_entries() == []


def test_entries_for_filters_in_sql():
    db.init_db(":memory:")
    db.save_entry(entry)
    other_day = {**entry, "date": "7/12/2026", "food": "rice"}
    db.save_entry(other_day)

    assert db.entries_for("7/11/2026") == [entry]
