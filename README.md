# Nutrition Tracker

A Python nutrition tracker that logs food entries and tallies calories, protein, carbs, and fat. One core module backs two frontends: a command-line tool and a deployed Streamlit web app.

## Demo

https://patrick-nutrition-tracker.streamlit.app/

Add a few foods and watch the macro totals update live. The deployed app keeps data only for your current browser session — see Design decisions for why.

## What it does

`make_entry()` and `total()` live in `project.py` and are shared by both frontends, so the logic exists in one place and the interfaces are just interfaces.

**Web app (`app.py`)** — a form for date, food, and the four macros. Submitting adds the entry to the running log and updates the totals for calories, protein, carbs, and fat. Entries live in the browser session and are gone when the tab closes; nothing is written to disk.

**Command-line tool (`project.py`)** — prompts for a date, then loops: food, calories, protein, carbs, fat, repeat. Saves to `entries.json` after every entry, so a crash mid-session doesn't lose the log, and reloads it on the next run. Press `Ctrl-D` (EOF) to finish and print the totals.

Note: entries store a date field, but totals currently sum *all* entries rather than filtering by day. Per-day filtering is planned (see Roadmap).

## Project structure

```
nutrition-tracker/
├── app.py                  # Streamlit web frontend
├── project.py              # CLI frontend + shared core logic
├── test_total.py           # Tests for total()
├── test_load_and_save.py   # Tests for JSON persistence
├── requirements.txt
└── README.md
```

`entries.json` is created by the CLI at runtime and is not tracked in the repo.

## How to run it

```bash
git clone https://github.com/patrickcoll1ns/nutrition-tracker.git
cd nutrition-tracker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Then either:

```bash
streamlit run app.py    # web app, opens in your browser
python project.py       # command-line tool
```

Built and deployed on Python 3.13. The core logic depends only on the Python standard library — Streamlit is used for the web frontend, pytest for the tests.

## Design decisions

- **The web app is a demo; the CLI is the tool.** The deployed app keeps entries in `st.session_state` and never calls `save()`. Streamlit Community Cloud's filesystem is long lasting *and* the deployed instance is shared across every visitor — writing to disk would leak my food log to strangers, let concurrent users clobber each other, and vanish on the next redeploy anyway. Persistence lives in the CLI, where it works correctly. Adding accounts and a hosted database would fix this properly, but that's a different project.
- **Input validation belongs in `app.py`, not `make_entry()`.** A web form can submit with fields blank in a way the CLI's `input()` never could, so the web app checks for a food name before building an entry. `make_entry()` stays a dumb constructor shared by both frontends rather than inheriting one frontend's input rules.
- **Flat list of dicts as the data structure.** Each food entry is one dict; the log is a list of them. Simple to iterate over and matches how the data is shaped naturally.
- **JSON for persistence, not CSV.** The data is already a list of dicts, and JSON preserves types — an int stays an int and a float stays a float on the round-trip, with no manual parsing. SQLite is a planned upgrade once the data outgrows a flat file.
- **Save after each entry, not once at the end.** A deliberate crash-safety tradeoff: writing more often costs a little I/O but means a crash mid-session doesn't wipe the log.
- **One parameterized `total(entries, macro)` function.** Replaced four near-identical functions (one per macro) with a single function that takes the macro name as an argument. Less duplication, easier to extend.

## Tests

```bash
pytest
```

The suite verifies:

- `total()` across all four macros
- `total()` on an empty log
- `total()` raising `KeyError` on an unknown macro
- `save()` / `load()` round-trip persistence
- `load()` returning an empty list when the file doesn't exist

## Roadmap

- **Per-day totals** — entries already carry a date; totals should filter by it.
- **Natural-language food logging** — parse free-text entries ("2 eggs and toast") into macros.