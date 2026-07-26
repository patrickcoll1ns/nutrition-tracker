"""SQLite persistence for nutrition log entries."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path


DEFAULT_DB_PATH = "entries.db"
ENTRY_COLUMNS = (
    "date",
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
            "CREATE INDEX IF NOT EXISTS idx_entries_date ON entries (date)"
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
    values = tuple(entry.get(column) for column in ENTRY_COLUMNS)
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
    values = tuple(entry.get(column) for column in ENTRY_COLUMNS)
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


def load_entries():
    """Return all entries using the dictionary shape expected by project.py."""
    return _fetch_entries()


def entries_for(date):
    """Return entries logged on one ISO-formatted date."""
    return _fetch_entries("WHERE date = ?", (date,))


def entries_with_ids_for(date):
    """Return entries for history management, including stable row IDs."""
    return _fetch_entries("WHERE date = ?", (date,), include_id=True)


def _fetch_entries(where_clause="", parameters=(), include_id=False):
    columns = ", ".join((("id",) if include_id else ()) + ENTRY_COLUMNS)
    with _connect() as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            f"SELECT {columns} FROM entries {where_clause} ORDER BY id",
            parameters,
        ).fetchall()
    return [dict(row) for row in rows]
