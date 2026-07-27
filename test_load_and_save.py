import sqlite3

import db

entry = {"date": "7/11/2026",
         "meal_type": "Dinner",
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


def test_entries_with_ids_returns_saved_row_id():
    db.init_db(":memory:")
    entry_id = db.save_entry(entry)

    assert db.entries_with_ids_for("7/11/2026") == [
        {"id": entry_id, **entry}
    ]


def test_update_entry():
    db.init_db(":memory:")
    entry_id = db.save_entry(entry)
    updated = {
        **entry,
        "date": "7/12/2026",
        "food": "grilled chicken",
        "calories": 210,
    }

    assert db.update_entry(entry_id, updated) is True
    assert db.load_entries() == [updated]
    assert db.update_entry(999, updated) is False


def test_delete_entry():
    db.init_db(":memory:")
    entry_id = db.save_entry(entry)

    assert db.delete_entry(entry_id) is True
    assert db.load_entries() == []
    assert db.delete_entry(entry_id) is False


def test_delete_multiple_entries():
    db.init_db(":memory:")
    first_id = db.save_entry(entry)
    second_id = db.save_entry({**entry, "food": "rice"})
    remaining_entry = {**entry, "food": "broccoli"}
    db.save_entry(remaining_entry)

    assert db.delete_entries([first_id, second_id]) == 2
    assert db.load_entries() == [remaining_entry]
    assert db.delete_entries([]) == 0


def test_delete_multiple_entries_ignores_duplicate_and_missing_ids():
    db.init_db(":memory:")
    entry_id = db.save_entry(entry)

    assert db.delete_entries([entry_id, entry_id, 999]) == 1
    assert db.load_entries() == []


def test_existing_database_gets_meal_type_column(tmp_path):
    database_path = tmp_path / "legacy.db"
    connection = sqlite3.connect(database_path)
    connection.execute(
        """
        CREATE TABLE entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            food TEXT NOT NULL,
            calories REAL NOT NULL,
            protein REAL NOT NULL,
            carbs REAL NOT NULL,
            fat REAL NOT NULL,
            usda_id INTEGER,
            usda_description TEXT,
            grams REAL
        )
        """
    )
    connection.execute(
        """
        INSERT INTO entries (
            date, food, calories, protein, carbs, fat,
            usda_id, usda_description, grams
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("2026-07-25", "egg", 78, 6.3, 0.6, 5.3, None, None, None),
    )
    connection.commit()
    connection.close()

    db.init_db(database_path)

    assert db.load_entries()[0]["meal_type"] == "Uncategorized"


def test_daily_totals_and_averages_for_current_period():
    db.init_db(":memory:")
    db.save_entry(entry)
    db.save_entry({**entry, "food": "rice", "calories": 110, "protein": 2})
    db.save_entry(
        {
            **entry,
            "date": "7/12/2026",
            "food": "egg",
            "calories": 100,
            "protein": 10,
        }
    )

    assert db.daily_totals_for_current_period() == [
        {
            "date": "7/11/2026",
            "calories": 300.0,
            "protein": 32.0,
            "carbs": 9.0,
            "fat": 0.6,
        },
        {
            "date": "7/12/2026",
            "calories": 100.0,
            "protein": 10.0,
            "carbs": 4.5,
            "fat": 0.3,
        },
    ]
    assert db.averages_for_current_period() == {
        "days_logged": 2,
        "calories": 200.0,
        "protein": 21.0,
        "carbs": 6.75,
        "fat": 0.45,
    }


def test_reset_averages_keeps_logs_and_starts_new_period():
    db.init_db(":memory:")
    db.save_entry(entry)

    assert db.reset_averages() is True
    assert db.load_entries() == [entry]
    assert db.averages_for_current_period()["days_logged"] == 0

    new_entry = {**entry, "date": "7/12/2026", "food": "rice"}
    db.save_entry(new_entry)

    assert db.daily_totals_for_current_period() == [
        {
            "date": "7/12/2026",
            "calories": 190.0,
            "protein": 30.0,
            "carbs": 4.5,
            "fat": 0.3,
        }
    ]
