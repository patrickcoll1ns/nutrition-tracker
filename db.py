"""SQLite persistence for nutrition log entries."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path


DEFAULT_DB_PATH = "entries.db"
LEGACY_USER_ID = "legacy"
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
                user_id TEXT NOT NULL DEFAULT 'legacy',
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
        if "user_id" not in existing_columns:
            connection.execute(
                """
                ALTER TABLE entries
                ADD COLUMN user_id TEXT NOT NULL DEFAULT 'legacy'
                """
            )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_entries_date ON entries (date)"
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_entries_user_date
            ON entries (user_id, date)
            """
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
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id TEXT PRIMARY KEY,
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


def save_entry(entry, user_id=LEGACY_USER_ID):
    """Insert one entry and return its database ID."""
    values = _entry_values(entry)
    with _connect() as connection:
        cursor = connection.execute(
            f"""
            INSERT INTO entries (user_id, {", ".join(ENTRY_COLUMNS)})
            VALUES (?, {", ".join("?" for _ in ENTRY_COLUMNS)})
            """,
            (user_id, *values),
        )
        return cursor.lastrowid


def update_entry(entry_id, entry, user_id=LEGACY_USER_ID):
    """Replace an entry's editable values. Return whether a row was updated."""
    values = _entry_values(entry)
    assignments = ", ".join(f"{column} = ?" for column in ENTRY_COLUMNS)
    with _connect() as connection:
        cursor = connection.execute(
            f"UPDATE entries SET {assignments} WHERE id = ? AND user_id = ?",
            (*values, entry_id, user_id),
        )
        return cursor.rowcount == 1


def delete_entry(entry_id, user_id=LEGACY_USER_ID):
    """Delete one entry by ID. Return whether a row was deleted."""
    with _connect() as connection:
        cursor = connection.execute(
            "DELETE FROM entries WHERE id = ? AND user_id = ?",
            (entry_id, user_id),
        )
        return cursor.rowcount == 1


def delete_entries(entry_ids, user_id=LEGACY_USER_ID):
    """Delete several entries in one transaction and return the number removed."""
    unique_ids = list(dict.fromkeys(entry_ids))
    if not unique_ids:
        return 0

    placeholders = ", ".join("?" for _ in unique_ids)
    with _connect() as connection:
        cursor = connection.execute(
            f"DELETE FROM entries WHERE user_id = ? AND id IN ({placeholders})",
            (user_id, *unique_ids),
        )
        return cursor.rowcount


def _entry_values(entry):
    return tuple(
        entry.get(column, "Uncategorized")
        if column == "meal_type"
        else entry.get(column)
        for column in ENTRY_COLUMNS
    )


def load_entries(user_id=LEGACY_USER_ID):
    """Return all entries using the dictionary shape expected by project.py."""
    return _fetch_entries("WHERE user_id = ?", (user_id,))


def entries_for(date, user_id=LEGACY_USER_ID):
    """Return entries logged on one ISO-formatted date."""
    return _fetch_entries(
        "WHERE user_id = ? AND date = ?", (user_id, date)
    )


def entries_with_ids_for(date, user_id=LEGACY_USER_ID):
    """Return entries for history management, including stable row IDs."""
    return _fetch_entries(
        "WHERE user_id = ? AND date = ?", (user_id, date), include_id=True
    )


def daily_totals_for_current_period(user_id=LEGACY_USER_ID):
    """Return daily totals for entries saved since the last average reset."""
    _ensure_user_settings(user_id)
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
            WHERE user_id = ?
            AND id > (
                SELECT average_reset_after_id
                FROM user_settings
                WHERE user_id = ?
            )
            GROUP BY date
            ORDER BY date
            """,
            (user_id, user_id),
        ).fetchall()
    return [dict(row) for row in rows]


def averages_for_current_period(user_id=LEGACY_USER_ID):
    """Return per-logged-day averages since the last reset."""
    _ensure_user_settings(user_id)
    daily_totals = daily_totals_for_current_period(user_id)
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


def reset_averages(user_id=LEGACY_USER_ID):
    """Start a new averaging period without deleting nutrition logs."""
    _ensure_user_settings(user_id)
    with _connect() as connection:
        cursor = connection.execute(
            """
            UPDATE user_settings
            SET average_reset_after_id = COALESCE(
                (SELECT MAX(id) FROM entries WHERE user_id = ?),
                0
            )
            WHERE user_id = ?
            """,
            (user_id, user_id),
        )
        return cursor.rowcount == 1


def nutrition_goals(user_id=LEGACY_USER_ID):
    """Return the user's saved daily calorie and macro goals."""
    _ensure_user_settings(user_id)
    with _connect() as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT calorie_goal, protein_goal, carb_goal, fat_goal
            FROM user_settings
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
    return {
        "calories": row["calorie_goal"],
        "protein": row["protein_goal"],
        "carbs": row["carb_goal"],
        "fat": row["fat_goal"],
    }


def update_nutrition_goals(goals, user_id=LEGACY_USER_ID):
    """Persist positive daily calorie and macro goals."""
    values = tuple(float(goals[macro]) for macro in DEFAULT_NUTRITION_GOALS)
    if any(value <= 0 for value in values):
        raise ValueError("Nutrition goals must be greater than zero.")

    _ensure_user_settings(user_id)
    with _connect() as connection:
        cursor = connection.execute(
            """
            UPDATE user_settings
            SET calorie_goal = ?,
                protein_goal = ?,
                carb_goal = ?,
                fat_goal = ?
            WHERE user_id = ?
            """,
            (*values, user_id),
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


def _ensure_user_settings(user_id):
    """Create an independent settings row the first time a user is seen."""
    with _connect() as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO user_settings (user_id)
            VALUES (?)
            """,
            (user_id,),
        )
