# Nutrition Tracker

A Python nutrition tracker that parses free-text meal descriptions ("two eggs and a slice of toast") into calories, protein, carbs, and fat using Claude for extraction and the USDA FoodData Central API for nutrition data. One core module backs two frontends: a command-line tool and a deployed Streamlit web app.

## Demo

https://patrick-nutrition-tracker.streamlit.app/

Describe a meal in plain English and watch the macro totals update live. Entries are stored in SQLite so they remain available across browser sessions.

Select a date to review its entries. Each entry can be expanded to correct its
date, meal category, name, or macro values, or permanently deleted after
clicking its delete button. New entries can be categorized as Breakfast, Lunch,
Dinner, or Snack.

Multiple entries from the selected date can also be selected and deleted
together in one action.

The trends section shows average daily calories and macros across logged days
in the current tracking period. Users can start a new averaging period without
deleting their history, and request an on-demand AI summary of the calculated
daily trends.

## What it does

`parse_meal()` in `project.py` is the shared pipeline behind both frontends:

1. Claude (`call_model`) extracts each distinct food, an estimated quantity, and a USDA-style search phrase from the description.
2. Each food is looked up against USDA FoodData Central (`call_usda`).
3. Claude re-ranks the USDA candidates against the original description (`select_best_match_llm`), falling back to a deterministic keyword-overlap heuristic (`select_best_match`) if the re-rank call fails or is inconclusive.
4. The matched USDA record's per-100g macros are scaled to the estimated portion size (`scale_macros`).

Foods that can't be matched to anything in USDA are reported back rather than silently dropped, so a partial parse doesn't quietly under-count your totals.

- Auto-stamps each entry with today's date, then repeatedly logs foods you ate.
- Both frontends save every entry to SQLite as soon as it is logged.
- Press `Ctrl-D` (EOF) to finish the CLI, at which point it prints **today's** total for each macro.

Entries accumulate across days in `entries.db`; daily summaries filter in SQL, so another day's food doesn't inflate the selected day's numbers.

## Project structure

```
nutrition-tracker/
├── app.py                  # Streamlit web frontend
├── db.py                   # Shared SQLite persistence layer
├── project.py              # CLI frontend + shared core logic (Claude + USDA pipeline)
├── test_*.py               # One test file per unit under test (see below)
├── usda_egg_response.json  # Fixture: a real USDA API response, used by test_parse_usda_response.py
├── requirements.txt
└── README.md
```

`entries.db` is created at runtime and is not tracked in the repo.

## How to run it

```bash
git clone https://github.com/patrickcoll1ns/nutrition-tracker.git
cd nutrition-tracker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

You'll also need API keys for [Anthropic](https://console.anthropic.com/) and [USDA FoodData Central](https://fdc.nal.usda.gov/api-key-signup.html). Put them in a `.env` file in the project root (gitignored, never committed):

```
ANTHROPIC_API_KEY=your-key-here
USDA_API_KEY=your-key-here
```

Then either:

```bash
streamlit run app.py    # web app, opens in your browser
python project.py       # command-line tool
```

Built and deployed on Python 3.13, using `anthropic`, `requests`, `python-dotenv`, and `streamlit` for the web frontend.

## Design decisions

- **One persistence layer for both frontends.** The CLI and Streamlit app read and write through `db.py`, so the database is the source of truth rather than browser session state.
- **Input validation belongs in `app.py`, not `make_entry()`.** A web form can submit with fields blank in a way the CLI's `input()` never could, so the web app checks for a food name before building an entry. `make_entry()` stays a dumb constructor shared by both frontends rather than inheriting one frontend's input rules.
- **SQLite with an internal row ID.** Callers still receive the same list-of-dicts shape, while each stored row has a stable ID that can support future edit and delete features. A date index keeps daily and trend queries efficient.
- **Save after each entry, not once at the end.** Each insert is committed immediately so a crash mid-session doesn't wipe the log.
- **One parameterized `total(entries, macro)` function.** Replaced four near-identical functions (one per macro) with a single function that takes the macro name as an argument. Less duplication, easier to extend.
- **Claude/USDA failures never reach the user as a raw traceback.** Both API-calling functions wrap their exceptions in a single `MealLookupError` with a message that's safe to display — in particular, it never echoes the raw `requests` exception, since that embeds the full request URL (including the USDA API key querystring) in its message.
- **Sane upper bounds on quantity, portion size, and foods-per-meal.** The Streamlit demo runs on a metered, shared API key; the extraction step is capped so a joke or adversarial description can't multiply into an unbounded number of USDA/Claude calls or an oversized in-memory list.

## Tests

```bash
pytest
```

Tests cover SQLite persistence and date filtering as well as the pure functions in `project.py`: response parsing/validation (including malformed and boundary-value LLM output), USDA response parsing (including malformed/incomplete nutrient data), the heuristic match fallback, macro scaling, and per-day totals.

`call_model`, `call_usda`, and `parse_meal` — the functions that actually touch the network — are covered by mocking the Claude/USDA calls rather than hitting the real APIs, so failure paths (timeouts, HTTP errors, unmatched foods) are exercised without needing live credentials in CI.

## Roadmap

- **Persistent accounts** — SQLite supports the current single-user app; a multi-user deployment still needs authentication and a hosted database.
- **Trend analysis** — add daily and weekly charts backed by the indexed log dates.
