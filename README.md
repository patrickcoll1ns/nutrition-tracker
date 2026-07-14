# Nutrition Tracker

A command-line nutrition tracker that logs food entries and tallies calories, protein, carbs, and fat. Data persists to disk as JSON, so entries survive across restarts.

## Demo

<!-- TODO: replace this with the live Streamlit URL once deployed. -->

*Live version coming soon — deploying a web UI to Streamlit Community Cloud.*

## What it does

- Prompts for a date, then repeatedly logs foods you ate along with their calories, protein, carbs, and fat.
- Saves after every entry, so a crash mid-session won't lose your data.
- Press `Ctrl-D` (EOF) to finish, at which point it prints the total for each macro across all logged entries.

Note: entries store a date field, but totals currently sum *all* entries in the file rather than filtering by day. Per-day filtering is planned alongside the web UI (see Roadmap).

## How to run it

```bash
git clone https://github.com/patrickcoll1ns/nutrition-tracker.git
cd nutrition-tracker
python project.py
```

Requires Python 3. The program itself uses only the standard library — no installs needed to run it. (`pytest` is used for the tests; see below.)

## Design decisions

- **Flat list of dicts as the data structure.** Each food entry is one dict; the log is a list of them. Simple to iterate over and matches how the data is shaped naturally.
- **JSON for persistence, not CSV.** The data is already a list of dicts, and JSON preserves types — an int stays an int and a float stays a float on the round-trip, with no manual parsing. SQLite is a planned upgrade once the data outgrows a flat file.
- **Save after each entry, not once at the end.** A deliberate crash-safety tradeoff: writing more often costs a little I/O but means a crash mid-session doesn't wipe the log.
- **One parameterized `total(entries, macro)` function.** Replaced four near-identical functions (one per macro) with a single function that takes the macro name as an argument. Less duplication, easier to extend.

## Tests

Run the suite with:

```bash
pip install pytest
pytest
```

The suite covers `total()` across all four macros, an empty log, and a missing-key error case; and `load`/`save` for both a successful round-trip and the missing-file fallback.

## Roadmap

- **Web UI** — deploy a Streamlit interface to Streamlit Community Cloud for a live, clickable URL, and resolve per-day totals at the same time.
- **Natural-language food logging** — parse free-text entries ("2 eggs and toast") into macros.