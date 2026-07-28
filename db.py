"""SQLite persistence for nutrition log entries."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path


DEFAULT_DB_PATH = "entries.db"
DEFAULT_NUTRITION_GOALS = {
    "calories": 2000.0,
    "protein": 100.0,
    "carbs": 275.0,
    "fat": 78.0,
}
ENTRY_COLUMNS = (
    "date",
    "meal_type",
    "food",
    "calories",
    "protein",
    "carbs",
    "fat",
    "usda_id",
    "usda_description",
    "grams",
)

_db_path = DEFAULT_DB_PATH
_memory_connection = None


def init_db(path=DEFAULT_DB_PATH):
    """Select a database and create the entries table when needed."""
    global _db_path, _memory_connection

    if _memory_connection is not None:
        _memory_connection.close()
        _memory_connection = None

    _db_path = str(path)
    if _db_path == ":memory:":
        _memory_connection = sqlite3.connect(":memory:")

    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                meal_type TEXT NOT NULL DEFAULT 'Uncategorized',
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
        existing_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(entries)")
        }
        if "meal_type" not in existing_columns:
            connection.execute(
                """
                ALTER TABLE entries
                ADD COLUMN meal_type TEXT NOT NULL DEFAULT 'Uncategorized'
                """
            )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_entries_date ON entries (date)"
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                average_reset_after_id INTEGER NOT NULL DEFAULT 0,
                calorie_goal REAL NOT NULL DEFAULT 2000,
                protein_goal REAL NOT NULL DEFAULT 100,
                carb_goal REAL NOT NULL DEFAULT 275,
                fat_goal REAL NOT NULL DEFAULT 78
            )
            """
        )
        settings_columns = {
            row[1] for row in connection.execute(
                "PRAGMA table_info(app_settings)"
            )
        }
        goal_columns = {
            "calorie_goal": DEFAULT_NUTRITION_GOALS["calories"],
            "protein_goal": DEFAULT_NUTRITION_GOALS["protein"],
            "carb_goal": DEFAULT_NUTRITION_GOALS["carbs"],
            "fat_goal": DEFAULT_NUTRITION_GOALS["fat"],
        }
        for column, default in goal_columns.items():
            if column not in settings_columns:
                connection.execute(
                    f"""
                    ALTER TABLE app_settings
                    ADD COLUMN {column} REAL NOT NULL DEFAULT {default:g}
                    """
                )
        connection.execute(
            """
            INSERT OR IGNORE INTO app_settings (
                id,
                average_reset_after_id,
                calorie_goal,
                protein_goal,
                carb_goal,
                fat_goal
            )
            VALUES (1, 0, 2000, 100, 275, 78)
            """
        )


@contextmanager
def _connect():
    if _db_path == ":memory:":
        if _memory_connection is None:
            raise RuntimeError("Call init_db() before using the database.")
        yield _memory_connection
        _memory_connection.commit()
        return

    connection = sqlite3.connect(Path(_db_path))
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def save_entry(entry):
    """Insert one entry and return its database ID."""
    values = _entry_values(entry)
    with _connect() as connection:
        cursor = connection.execute(
            f"""
            INSERT INTO entries ({", ".join(ENTRY_COLUMNS)})
            VALUES ({", ".join("?" for _ in ENTRY_COLUMNS)})
            """,
            values,
        )
        return cursor.lastrowid


def update_entry(entry_id, entry):
    """Replace an entry's editable values. Return whether a row was updated."""
    values = _entry_values(entry)
    assignments = ", ".join(f"{column} = ?" for column in ENTRY_COLUMNS)
    with _connect() as connection:
        cursor = connection.execute(
            f"UPDATE entries SET {assignments} WHERE id = ?",
            (*values, entry_id),
        )
        return cursor.rowcount == 1


def delete_entry(entry_id):
    """Delete one entry by ID. Return whether a row was deleted."""
    with _connect() as connection:
        cursor = connection.execute(
            "DELETE FROM entries WHERE id = ?",
            (entry_id,),
        )
        return cursor.rowcount == 1


def delete_entries(entry_ids):
    """Delete several entries in one transaction and return the number removed."""
    unique_ids = list(dict.fromkeys(entry_ids))
    if not unique_ids:
        return 0

    placeholders = ", ".join("?" for _ in unique_ids)
    with _connect() as connection:
        cursor = connection.execute(
            f"DELETE FROM entries WHERE id IN ({placeholders})",
            unique_ids,
        )
        return cursor.rowcount


def _entry_values(entry):
    return tuple(
        entry.get(column, "Uncategorized")
        if column == "meal_type"
        else entry.get(column)
        for column in ENTRY_COLUMNS
    )


def load_entries():
    """Return all entries using the dictionary shape expected by project.py."""
    return _fetch_entries()


def entries_for(date):
    """Return entries logged on one ISO-formatted date."""
    return _fetch_entries("WHERE date = ?", (date,))


def entries_with_ids_for(date):
    """Return entries for history management, including stable row IDs."""
    return _fetch_entries("WHERE date = ?", (date,), include_id=True)


def daily_totals_for_current_period():
    """Return daily totals for entries saved since the last average reset."""
    with _connect() as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT
                date,
                ROUND(SUM(calories), 2) AS calories,
                ROUND(SUM(protein), 2) AS protein,
                ROUND(SUM(carbs), 2) AS carbs,
                ROUND(SUM(fat), 2) AS fat
            FROM entries
            WHERE id > (
                SELECT average_reset_after_id
                FROM app_settings
                WHERE id = 1
            )
            GROUP BY date
            ORDER BY date
            """
        ).fetchall()
    return [dict(row) for row in rows]


def averages_for_current_period():
    """Return per-logged-day averages since the last reset."""
    daily_totals = daily_totals_for_current_period()
    if not daily_totals:
        return {
            "days_logged": 0,
            "calories": 0,
            "protein": 0,
            "carbs": 0,
            "fat": 0,
        }

    return {
        "days_logged": len(daily_totals),
        **{
            macro: round(
                sum(day[macro] for day in daily_totals) / len(daily_totals),
                2,
            )
            for macro in ("calories", "protein", "carbs", "fat")
        },
    }


def reset_averages():
    """Start a new averaging period without deleting nutrition logs."""
    with _connect() as connection:
        cursor = connection.execute(
            """
            UPDATE app_settings
            SET average_reset_after_id = COALESCE(
                (SELECT MAX(id) FROM entries),
                0
            )
            WHERE id = 1
            """
        )
        return cursor.rowcount == 1


def nutrition_goals():
    """Return the user's saved daily calorie and macro goals."""
    with _connect() as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT calorie_goal, protein_goal, carb_goal, fat_goal
            FROM app_settings
            WHERE id = 1
            """
        ).fetchone()
    return {
        "calories": row["calorie_goal"],
        "protein": row["protein_goal"],
        "carbs": row["carb_goal"],
        "fat": row["fat_goal"],
    }


def update_nutrition_goals(goals):
    """Persist positive daily calorie and macro goals."""
    values = tuple(float(goals[macro]) for macro in DEFAULT_NUTRITION_GOALS)
    if any(value <= 0 for value in values):
        raise ValueError("Nutrition goals must be greater than zero.")

    with _connect() as connection:
        cursor = connection.execute(
            """
            UPDATE app_settings
            SET calorie_goal = ?,
                protein_goal = ?,
                carb_goal = ?,
                fat_goal = ?
            WHERE id = 1
            """,
            values,
        )
        return cursor.rowcount == 1


def _fetch_entries(where_clause="", parameters=(), include_id=False):
    columns = ", ".join((("id",) if include_id else ()) + ENTRY_COLUMNS)
    with _connect() as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            f"SELECT {columns} FROM entries {where_clause} ORDER BY id",
            parameters,
        ).fetchall()
    return [dict(row) for row in rows]
