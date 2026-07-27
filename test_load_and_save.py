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
