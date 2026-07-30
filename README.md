# Nourish — Nutrition Tracker

A responsive Python nutrition tracker that turns free-text meal descriptions
("two eggs and a slice of toast") into calories, protein, carbs, and fat using
Claude for extraction and the USDA FoodData Central API for nutrition data. One
core module backs two frontends: a command-line tool and the Nourish Streamlit
web app.

## Demo

https://patrick-nutrition-tracker.streamlit.app/

Describe a meal in plain English and watch the dashboard update with calorie
and macro totals. People sign in with Google, and entries, nutrition goals, and
tracking-period settings are isolated by account. They are stored in SQLite so
they remain available across browser sessions while the deployment's local
storage exists.

Google sign-in is used only to identify the account that owns each nutrition
record. Nourish does not receive or store Google passwords. A signed-in person
can only load, edit, or delete records associated with their own Google account
identifier.

The web interface is organized into four areas:

- **Add meal** — analyze a natural-language description or open the manual form
  to enter known nutrition values.
- **Dashboard** — review the selected day's meals, totals, and progress toward
  configurable calorie, protein, carbohydrate, and fat goals.
- **Insights** — view daily averages, a four-series nutrition trend chart, and
  an optional AI-generated analysis.
- **History** — edit or delete entries from the selected date.

Meals can be categorized as Breakfast, Lunch, Dinner, or Snack. Multiple
entries can be selected and deleted together, and individual entries can be
expanded to correct their date, category, name, or nutrition values.

Users can choose their own daily goals from the Dashboard. Each progress card
shows the percentage completed and the amount remaining—or the amount over the
goal. Saved goals persist in the database and existing databases are
automatically migrated with sensible defaults.

## What it does

`parse_meal()` in `project.py` is the shared pipeline behind both frontends:

1. Claude (`call_model`) extracts each distinct food, an estimated quantity, and a USDA-style search phrase from the description.
2. Each food is looked up against USDA FoodData Central (`call_usda`).
3. Claude re-ranks the USDA candidates against the original description (`select_best_match_llm`), falling back to a deterministic keyword-overlap heuristic (`select_best_match`) if the re-rank call fails or is inconclusive.
4. The matched USDA record's per-100g macros are scaled to the estimated portion size (`scale_macros`).

Foods that can't be matched to anything in USDA are reported back rather than silently dropped, so a partial parse doesn't quietly under-count your totals.

- Defaults new entries to today's date while allowing another date to be
  selected in the web app.
- Saves every entry to SQLite immediately.
- Displays daily totals against user-selected calorie and macro goals.
- Charts calories, protein, carbohydrates, and fat across the current tracking
  period.
- Lets users reset the averaging period without deleting their meal history.
- Prints today's macro totals when the CLI exits with `Ctrl-D` (EOF).

Entries accumulate across days in `entries.db`; daily summaries filter in SQL, so another day's food doesn't inflate the selected day's numbers.

Default daily goals are 2,000 kcal, 100 g protein, 275 g carbohydrates, and
78 g fat. They are starting values only and can be changed from the Dashboard.

## Project structure

```
nutrition-tracker/
├── .streamlit/
│   └── secrets.toml.example # Safe template for local authentication settings
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

### Configure Google sign-in

Create a **Web application** OAuth client in Google Cloud. Add both application
origins under **Authorized JavaScript origins**:

- `http://localhost:8501`
- `https://patrick-nutrition-tracker.streamlit.app`

Add both callback addresses under **Authorized redirect URIs**:

- `http://localhost:8501/oauth2callback` for local development
- `https://patrick-nutrition-tracker.streamlit.app/oauth2callback` for the
  deployed app

For local development, copy the included example (the resulting secrets file
is gitignored):

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Then replace the placeholder values in `.streamlit/secrets.toml`:

```toml
[auth]
redirect_uri = "http://localhost:8501/oauth2callback"
cookie_secret = "generate-a-long-random-value"
client_id = "your-google-client-id"
client_secret = "your-google-client-secret"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

For Streamlit Community Cloud, open **Manage app → Settings → Secrets** and add
the API keys and production authentication configuration:

```toml
ANTHROPIC_API_KEY = "your-anthropic-key"
USDA_API_KEY = "your-usda-key"

[auth]
redirect_uri = "https://patrick-nutrition-tracker.streamlit.app/oauth2callback"
cookie_secret = "generate-a-long-random-value"
client_id = "your-google-client-id.apps.googleusercontent.com"
client_secret = "your-google-client-secret"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

The local and deployed configurations use the same Google client ID and client
secret, but different `redirect_uri` values. Save the Cloud secrets and reboot
the app so Streamlit initializes authentication. Never commit
`.streamlit/secrets.toml`, OAuth credentials, cookie secrets, or API keys.

### Authentication troubleshooting

- **`Error 401: invalid_client` / “OAuth client was not found”** — the deployed
  `client_id` is missing, still a placeholder, or does not exactly match the
  Google client. Copy the complete ID that works locally into Streamlit Cloud
  Secrets; a Google web client ID normally ends in
  `.apps.googleusercontent.com`.
- **`redirect_uri_mismatch`** — the callback in Streamlit Secrets does not
  exactly match an Authorized redirect URI in Google Cloud. Local development
  uses the HTTP localhost callback; the deployed app uses the HTTPS
  `streamlit.app` callback shown above.
- **“Google sign-in is not configured”** — the `[auth]` block is absent,
  incomplete, or has not been loaded. Correct the Cloud Secrets, save them, and
  reboot the app.

Then either:

```bash
streamlit run app.py    # web app, opens in your browser
python project.py       # command-line tool
```

Built and deployed on Python 3.13, using `anthropic`, `requests`,
`python-dotenv`, `pandas`, and `streamlit`.

## Design decisions

- **One persistence layer for both frontends.** The CLI and Streamlit app read and write through `db.py`, so the database is the source of truth rather than browser session state.
- **Private account-scoped web logs.** Streamlit's OIDC sign-in supplies a
  stable Google account identifier. Every web query, insert, update, and delete
  includes that identifier, including goals and averaging-period settings.
  Existing records from before accounts were added remain assigned to an
  isolated legacy identity rather than becoming visible to a new user.
- **Input validation belongs in `app.py`, not `make_entry()`.** A web form can submit with fields blank in a way the CLI's `input()` never could, so the web app checks for a food name before building an entry. `make_entry()` stays a dumb constructor shared by both frontends rather than inheriting one frontend's input rules.
- **SQLite with an internal row ID.** Callers still receive the same list-of-dicts shape, while each stored row has a stable ID that can support future edit and delete features. A date index keeps daily and trend queries efficient.
- **Save after each entry, not once at the end.** Each insert is committed immediately so a crash mid-session doesn't wipe the log.
- **Goals live beside each user's data.** Daily calorie and macro goals are
  stored in `user_settings`, keyed by the same account identifier as meal
  entries. Each person's targets and averaging reset are independent.
- **Progress is calculated at render time.** Saved goals remain independent
  from logged meals; the Dashboard compares the selected day's totals with the
  current targets and reports percentage complete, remaining values, or
  overages.
- **Trends use daily aggregates.** Pandas converts the database's per-day totals
  into a date-indexed frame for Streamlit's four-series line chart, while an
  empty state handles periods without logged meals.
- **One parameterized `total(entries, macro)` function.** Replaced four near-identical functions (one per macro) with a single function that takes the macro name as an argument. Less duplication, easier to extend.
- **Claude/USDA failures never reach the user as a raw traceback.** Both API-calling functions wrap their exceptions in a single `MealLookupError` with a message that's safe to display — in particular, it never echoes the raw `requests` exception, since that embeds the full request URL (including the USDA API key querystring) in its message.
- **Sane upper bounds on quantity, portion size, and foods-per-meal.** The Streamlit demo runs on a metered, shared API key; the extraction step is capped so a joke or adversarial description can't multiply into an unbounded number of USDA/Claude calls or an oversized in-memory list.

## Tests

```bash
pytest
```

Tests cover SQLite persistence, date filtering, configurable nutrition goals,
legacy-database migration, daily trends, and the pure functions in `project.py`:
response parsing/validation (including malformed and boundary-value LLM
output), USDA response parsing (including malformed/incomplete nutrient data),
the heuristic match fallback, macro scaling, and per-day totals.

`call_model`, `call_usda`, and `parse_meal` — the functions that actually touch the network — are covered by mocking the Claude/USDA calls rather than hitting the real APIs, so failure paths (timeouts, HTTP errors, unmatched foods) are exercised without needing live credentials in CI.

## Roadmap

- **Hosted persistence** — move production data from SQLite to a hosted
  database. Streamlit Community Cloud does not guarantee that files written to
  its local filesystem will persist indefinitely.
- **Goal guidance** — optionally calculate suggested targets from user-provided
  preferences while keeping the final goals editable.
- **Richer insights** — add selectable 7-, 30-, and 90-day chart ranges and
  macro-specific views.
