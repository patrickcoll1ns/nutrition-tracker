import os
import traceback
from collections import Counter, defaultdict
from datetime import date as calendar_date
import html
from urllib.parse import urlsplit

import pandas as pd
import streamlit as st
from project import (
    total,
    make_entry,
    parse_meal,
    analyze_nutrition_trends,
    MealLookupError,
    MEAL_TYPES,
)
import db

st.set_page_config(
    page_title="Nourish · Nutrition tracker",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Streamlit gives us the interaction model; this small design layer gives the
# app a warmer, calmer visual identity without coupling the core logic to a
# separate frontend.
st.markdown(
    """
    <style>
        :root {
            --nourish-green: #5f8f72;
            --nourish-green-dark: #426951;
            --nourish-coral: #e88467;
            --nourish-amber: #e8b35d;
            --nourish-ink: #23332a;
            --nourish-muted: #69766e;
            --nourish-surface: rgba(255, 255, 255, 0.72);
            --nourish-border: rgba(95, 143, 114, 0.20);
        }

        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at 8% 0%, rgba(120, 171, 139, 0.14), transparent 26rem),
                radial-gradient(circle at 95% 8%, rgba(232, 132, 103, 0.10), transparent 24rem),
                #f7f5ef;
            color: var(--nourish-ink);
        }

        [data-testid="stHeader"] {
            background: transparent;
        }

        .block-container {
            max-width: 1080px;
            padding-top: 2.4rem;
            padding-bottom: 5rem;
        }

        h1, h2, h3 {
            color: var(--nourish-ink);
            letter-spacing: -0.035em;
        }

        h1 {
            font-size: clamp(2.35rem, 5vw, 4.25rem) !important;
            line-height: 1.02 !important;
            margin-bottom: 0.45rem !important;
        }

        h3 {
            margin-top: 0.7rem !important;
        }

        .nourish-eyebrow {
            color: var(--nourish-green-dark);
            font-size: 0.78rem;
            font-weight: 750;
            letter-spacing: 0.14em;
            margin: 0 0 0.6rem;
            text-transform: uppercase;
        }

        .nourish-subtitle {
            color: var(--nourish-muted);
            font-size: 1.08rem;
            line-height: 1.6;
            margin: 0 0 1.8rem;
            max-width: 42rem;
        }

        .nourish-section-copy {
            color: var(--nourish-muted);
            margin: -0.35rem 0 1.15rem;
        }

        .nourish-card {
            background: var(--nourish-surface);
            border: 1px solid var(--nourish-border);
            border-radius: 18px;
            box-shadow: 0 14px 40px rgba(43, 66, 52, 0.06);
            margin: 0.35rem 0 1rem;
            padding: 1.15rem 1.25rem;
        }

        .nourish-card-label {
            color: var(--nourish-muted);
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }

        .nourish-card-value {
            color: var(--nourish-ink);
            font-size: 1.8rem;
            font-weight: 750;
            letter-spacing: -0.04em;
            margin-top: 0.15rem;
        }

        .nourish-card-unit {
            color: var(--nourish-muted);
            font-size: 0.88rem;
            font-weight: 500;
        }

        .nourish-progress {
            background: rgba(95, 143, 114, 0.13);
            border-radius: 99px;
            height: 7px;
            margin-top: 0.75rem;
            overflow: hidden;
        }

        .nourish-progress > span {
            background: linear-gradient(90deg, var(--nourish-green), #84ad91);
            border-radius: inherit;
            display: block;
            height: 100%;
        }

        .nourish-goal-copy {
            color: var(--nourish-muted);
            display: flex;
            font-size: 0.76rem;
            justify-content: space-between;
            margin-top: 0.48rem;
        }

        .nourish-empty {
            background: rgba(255, 255, 255, 0.56);
            border: 1px dashed rgba(95, 143, 114, 0.36);
            border-radius: 18px;
            color: var(--nourish-muted);
            padding: 2rem;
            text-align: center;
        }

        .nourish-empty strong {
            color: var(--nourish-ink);
            display: block;
            font-size: 1.05rem;
            margin-bottom: 0.3rem;
        }

        .nourish-meal-row {
            align-items: center;
            background: rgba(255, 255, 255, 0.55);
            border: 1px solid var(--nourish-border);
            border-radius: 14px;
            display: flex;
            justify-content: space-between;
            margin: 0.55rem 0;
            padding: 0.85rem 1rem;
        }

        .nourish-meal-name {
            color: var(--nourish-ink);
            font-weight: 700;
        }

        .nourish-badge {
            background: rgba(95, 143, 114, 0.12);
            border-radius: 99px;
            color: var(--nourish-green-dark);
            font-size: 0.72rem;
            font-weight: 700;
            margin-left: 0.45rem;
            padding: 0.24rem 0.55rem;
        }

        .nourish-meal-calories {
            color: var(--nourish-muted);
            font-size: 0.9rem;
            white-space: nowrap;
        }

        [data-testid="stTabs"] [data-baseweb="tab-list"] {
            background: rgba(255, 255, 255, 0.52);
            border: 1px solid var(--nourish-border);
            border-radius: 14px;
            gap: 0.2rem;
            padding: 0.28rem;
        }

        [data-testid="stTabs"] button[role="tab"] {
            border-radius: 10px;
            padding-left: 1rem;
            padding-right: 1rem;
        }

        [data-testid="stTabs"] button[aria-selected="true"] {
            background: rgba(95, 143, 114, 0.12);
            color: var(--nourish-green-dark);
        }

        [data-testid="stTabs"] [data-baseweb="tab-highlight"] {
            background-color: var(--nourish-green);
        }

        [data-testid="stForm"],
        [data-testid="stExpander"] {
            background: rgba(255, 255, 255, 0.48);
            border-color: var(--nourish-border);
            border-radius: 16px;
        }

        .stButton > button,
        [data-testid="stFormSubmitButton"] > button {
            border-radius: 11px;
            font-weight: 700;
            min-height: 2.65rem;
        }

        .stButton > button[kind="primary"],
        [data-testid="stFormSubmitButton"] > button[kind="primary"] {
            background: var(--nourish-green);
            border-color: var(--nourish-green);
        }

        [data-baseweb="input"] > div,
        [data-baseweb="select"] > div {
            border-radius: 11px;
        }

        @media (prefers-color-scheme: dark) {
            [data-testid="stAppViewContainer"] {
                background:
                    radial-gradient(circle at 8% 0%, rgba(95, 143, 114, 0.14), transparent 26rem),
                    radial-gradient(circle at 95% 8%, rgba(232, 132, 103, 0.08), transparent 24rem),
                    #111713;
            }
            :root {
                --nourish-ink: #eef3ef;
                --nourish-muted: #a5b1a9;
                --nourish-surface: rgba(29, 39, 32, 0.72);
                --nourish-border: rgba(139, 180, 153, 0.18);
            }
            .nourish-empty,
            .nourish-meal-row,
            [data-testid="stTabs"] [data-baseweb="tab-list"],
            [data-testid="stForm"],
            [data-testid="stExpander"] {
                background: rgba(29, 39, 32, 0.62);
            }
        }

        @media (max-width: 640px) {
            .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
                padding-top: 1.2rem;
            }
            h1 {
                font-size: 2.45rem !important;
            }
            .nourish-subtitle {
                font-size: 0.98rem;
                margin-bottom: 1.25rem;
            }
            [data-testid="stTabs"] [data-baseweb="tab-list"] {
                overflow-x: auto;
            }
            [data-testid="stTabs"] button[role="tab"] {
                font-size: 0.8rem;
                padding-left: 0.65rem;
                padding-right: 0.65rem;
            }
            .nourish-meal-row {
                align-items: flex-start;
                gap: 0.55rem;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_macro_card(label, value, unit, target):
    """Render a compact daily-progress card."""
    progress = min((float(value) / target) * 100, 100) if target else 0
    remaining = target - float(value)
    status = (
        f"{remaining:g} {unit} left"
        if remaining >= 0
        else f"{abs(remaining):g} {unit} over"
    )
    st.markdown(
        f"""
        <div class="nourish-card">
            <div class="nourish-card-label">{label}</div>
            <div class="nourish-card-value">
                {float(value):g} <span class="nourish-card-unit">{unit}</span>
            </div>
            <div class="nourish-progress" title="{progress:.0f}% of daily goal">
                <span style="width: {progress:.1f}%"></span>
            </div>
            <div class="nourish-goal-copy">
                <span>{progress:.0f}%</span>
                <span>{status} · goal {target:g}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# Bridge Streamlit Cloud's secrets into the environment so project.py
# can stay streamlit-free and keep reading os.environ.
try:
    os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
    os.environ["USDA_API_KEY"] = st.secrets["USDA_API_KEY"]
except Exception:
    pass

st.markdown('<p class="nourish-eyebrow">Daily nutrition, made simple</p>', unsafe_allow_html=True)
st.title("Nourish")
st.markdown(
    '<p class="nourish-subtitle">Log meals in everyday language, see the '
    "nutrition behind them, and build a clearer picture of your habits.</p>",
    unsafe_allow_html=True,
)

try:
    is_logged_in = st.user.is_logged_in
except AttributeError:
    st.error("Google sign-in is not configured for this copy of Nourish.")
    try:
        auth_settings = st.secrets.get("auth", {})
    except Exception:
        auth_settings = {}
    required_auth_keys = {
        "redirect_uri",
        "cookie_secret",
        "client_id",
        "client_secret",
        "server_metadata_url",
    }
    missing_auth_keys = sorted(required_auth_keys - set(auth_settings))
    current_url = st.context.url
    current_origin = (
        f"{urlsplit(current_url).scheme}://{urlsplit(current_url).netloc}"
    )
    expected_redirect_uri = f"{current_origin}/oauth2callback"

    if not auth_settings:
        st.markdown(
            "No `[auth]` section was found. Add it in "
            "**Manage app → Settings → Secrets**, save, and reboot the app."
        )
    elif missing_auth_keys:
        st.markdown(
            "The `[auth]` section is missing: "
            + ", ".join(f"`{key}`" for key in missing_auth_keys)
            + "."
        )
    elif auth_settings["redirect_uri"] != expected_redirect_uri:
        st.markdown(
            "The configured `redirect_uri` does not match this app. "
            f"It must be exactly: `{expected_redirect_uri}`"
        )
    else:
        st.markdown(
            "The authentication values are present, but Streamlit has not "
            "loaded them yet. Reboot the app from **Manage app**."
        )
    st.stop()

if not is_logged_in:
    st.info("Sign in to keep your food log private and separate from everyone else’s.")
    st.button(
        "Continue with Google",
        type="primary",
        on_click=st.login,
    )
    st.stop()

user_id = st.user.get("sub")
if not user_id:
    st.error("Your sign-in did not include a stable account identifier. Please sign out and try again.")
    st.button("Sign out", on_click=st.logout)
    st.stop()

account_columns = st.columns([5, 1])
account_columns[0].caption(
    f'Signed in as {st.user.get("name") or st.user.get("email") or "your account"}'
)
account_columns[1].button("Sign out", on_click=st.logout)

db.init_db()

if "entry_message" in st.session_state:
    st.success(st.session_state.pop("entry_message"))

log_tab, summary_tab, trends_tab, history_tab = st.tabs(
    ["＋ Add meal", "Dashboard", "Insights", "History"]
)

with log_tab:
    st.subheader("Add a meal")
    st.markdown(
        '<p class="nourish-section-copy">Tell us what you ate—we’ll do the '
        "nutrient math for you.</p>",
        unsafe_allow_html=True,
    )

    # Shared by both logging paths, so it has to live above both of them.
    meal_context_columns = st.columns([1, 1])
    date = meal_context_columns[0].date_input("Date").isoformat()
    meal_type = meal_context_columns[1].selectbox("Meal category", MEAL_TYPES)

    st.markdown("#### Describe your meal")
    description = st.text_input(
        "What did you eat?",
        max_chars=300,
        placeholder="e.g. 2 eggs, avocado toast, and a cup of coffee",
    )

    if st.button("Analyze & add meal", type="primary", width="stretch"):
        if not description.strip():
            st.error("Type a meal description first.")
        else:
            parsed, unmatched = None, []
            try:
                with st.spinner("Parsing..."):
                    parsed, unmatched = parse_meal(description)
            except MealLookupError as e:
                # Message is pre-sanitized in project.py — safe to show as-is,
                # and it correctly identifies which service failed.
                st.error(str(e))
            except Exception:
                # Don't show unexpected exception text to end users.
                st.error("Something went wrong parsing that meal. Try again, or use the manual form below.")
                traceback.print_exc()

            if parsed is None:
                pass  # error already showed above
            elif not parsed and not unmatched:
                st.warning("I could not find any food in that description.")
            else:
                for item in parsed:
                    entry = make_entry(
                        date,
                        item["food"],
                        meal_type=meal_type,
                        calories=item["calories"],
                        protein=item["protein"],
                        carbs=item["carbs"],
                        fat=item["fat"],
                        usda_id=item["usda_id"],
                        usda_description=item["usda_description"],
                        grams=item["grams"],
                    )
                    db.save_entry(entry, user_id)
                if parsed:
                    st.success(f"Logged {len(parsed)} item(s).")
                if unmatched:
                    st.warning(f"Couldn't find a USDA match for: {', '.join(unmatched)} — not logged.")

    with st.expander("Enter nutrition manually"):
        st.caption("Use this when you already know the nutrition values.")
        with st.form("entry_form", clear_on_submit=True):
            food = st.text_input("Food", placeholder="Food name")
            manual_columns = st.columns(2)
            calories = manual_columns[0].number_input(
                "Calories", min_value=0, step=1
            )
            protein = manual_columns[1].number_input(
                "Protein (g)", min_value=0.0, step=0.1
            )
            carbs = manual_columns[0].number_input(
                "Carbs (g)", min_value=0.0, step=0.1
            )
            fat = manual_columns[1].number_input(
                "Fat (g)", min_value=0.0, step=0.1
            )
            submitted = st.form_submit_button(
                "Add manual entry",
                type="primary",
                width="stretch",
            )

    if submitted:
        if not food.strip():
            st.error("Enter a food name before making an entry.")
        else:
            entry = make_entry(
                date,
                food,
                meal_type=meal_type,
                calories=calories,
                protein=protein,
                carbs=carbs,
                fat=fat,
                usda_id=None,
                usda_description=None,
                grams=None,
            )
            db.save_entry(entry, user_id)

entries = db.entries_with_ids_for(date, user_id)
total_calories = total(entries, "calories")
total_protein = total(entries, "protein")
total_carbs = total(entries, "carbs")
total_fat = total(entries, "fat")
nutrition_goals = db.nutrition_goals(user_id)

with summary_tab:
    st.subheader("Today:")
    st.markdown(
        '<p class="nourish-section-copy">Your totals for the selected date. '
        "Progress bars track the daily goals you choose.</p>",
        unsafe_allow_html=True,
    )

    with st.expander("Set daily goals"):
        st.caption(
            "Choose the daily calorie and macro targets that fit your plan."
        )
        with st.form("nutrition_goals_form"):
            goal_columns = st.columns(4)
            calorie_goal = goal_columns[0].number_input(
                "Calories (kcal)",
                min_value=1.0,
                value=float(nutrition_goals["calories"]),
                step=50.0,
            )
            protein_goal = goal_columns[1].number_input(
                "Protein (g)",
                min_value=1.0,
                value=float(nutrition_goals["protein"]),
                step=5.0,
            )
            carb_goal = goal_columns[2].number_input(
                "Carbs (g)",
                min_value=1.0,
                value=float(nutrition_goals["carbs"]),
                step=5.0,
            )
            fat_goal = goal_columns[3].number_input(
                "Fat (g)",
                min_value=1.0,
                value=float(nutrition_goals["fat"]),
                step=5.0,
            )
            save_goals = st.form_submit_button(
                "Save daily goals",
                type="primary",
                width="stretch",
            )

        if save_goals:
            db.update_nutrition_goals(
                {
                    "calories": calorie_goal,
                    "protein": protein_goal,
                    "carbs": carb_goal,
                    "fat": fat_goal,
                },
                user_id,
            )
            st.session_state["entry_message"] = "Daily goals updated."
            st.rerun()

    metric_columns = st.columns(4)
    with metric_columns[0]:
        render_macro_card(
            "Calories",
            total_calories,
            "kcal",
            nutrition_goals["calories"],
        )
    with metric_columns[1]:
        render_macro_card(
            "Protein",
            total_protein,
            "g",
            nutrition_goals["protein"],
        )
    with metric_columns[2]:
        render_macro_card(
            "Carbs",
            total_carbs,
            "g",
            nutrition_goals["carbs"],
        )
    with metric_columns[3]:
        render_macro_card(
            "Fat",
            total_fat,
            "g",
            nutrition_goals["fat"],
        )

    st.markdown("#### Meals")
    if not entries:
        st.markdown(
            """
            <div class="nourish-empty">
                <strong>Nothing logged yet</strong>
                Add your first meal to see today’s nutrition breakdown.
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        for entry in entries:
            st.markdown(
                f"""
                <div class="nourish-meal-row">
                    <div>
                        <span class="nourish-meal-name">{html.escape(entry["food"])}</span>
                        <span class="nourish-badge">{html.escape(entry["meal_type"])}</span>
                    </div>
                    <span class="nourish-meal-calories">{entry["calories"]:g} kcal</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

with trends_tab:
    st.subheader("Nutrition insights")
    averages = db.averages_for_current_period(user_id)
    st.caption(
        f'Average across {averages["days_logged"]} logged day(s) since the '
        "last reset. Days without logs are not included."
    )

    average_columns = st.columns(4)
    average_columns[0].metric("Calories / day", averages["calories"])
    average_columns[1].metric("Protein / day", f'{averages["protein"]} g')
    average_columns[2].metric("Carbs / day", f'{averages["carbs"]} g')
    average_columns[3].metric("Fat / day", f'{averages["fat"]} g')

    st.markdown("#### Daily trend")
    daily_totals = db.daily_totals_for_current_period(user_id)
    if daily_totals:
        trend_data = pd.DataFrame(daily_totals)
        trend_data["date"] = pd.to_datetime(trend_data["date"])
        trend_data = trend_data.set_index("date")[
            ["calories", "protein", "carbs", "fat"]
        ]
        trend_data.columns = ["Calories", "Protein", "Carbs", "Fat"]
        st.line_chart(
            trend_data,
            color=["#5f8f72", "#e88467", "#e8b35d", "#7897b5"],
            width="stretch",
        )
        st.caption(
            "Calories are measured in kcal; protein, carbs, and fat are measured in grams."
        )
    else:
        st.info("Log a meal to see your trend chart.")

    trend_action_columns = st.columns(2)
    if trend_action_columns[0].button(
        "Analyze trends with AI",
        disabled=averages["days_logged"] == 0,
    ):
        try:
            with st.spinner("Analyzing your logged trends..."):
                st.session_state["trend_analysis"] = analyze_nutrition_trends(
                    db.daily_totals_for_current_period(user_id)
                )
        except MealLookupError as e:
            st.error(str(e))

    if trend_action_columns[1].button("Reset averages"):
        db.reset_averages(user_id)
        st.session_state.pop("trend_analysis", None)
        st.session_state["entry_message"] = (
            "A new averaging period has started. Your food logs were not deleted."
        )
        st.rerun()

    if "trend_analysis" in st.session_state:
        st.write(st.session_state["trend_analysis"])

with history_tab:
    st.subheader("Meal history")
    st.markdown(
        '<p class="nourish-section-copy">Review or correct anything logged '
        "for the selected date.</p>",
        unsafe_allow_html=True,
    )

    if not entries:
        st.markdown(
            """
            <div class="nourish-empty">
                <strong>No meals on this date</strong>
                Choose another date or add a meal to get started.
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        entry_names = [
            (entry["meal_type"], entry["food"], entry["calories"])
            for entry in entries
        ]
        duplicate_counts = Counter(entry_names)
        occurrence_counts = defaultdict(int)
        entry_labels = {}
        for entry, entry_name in zip(entries, entry_names):
            occurrence_counts[entry_name] += 1
            duplicate_label = ""
            if duplicate_counts[entry_name] > 1:
                duplicate_label = (
                    f" ({occurrence_counts[entry_name]} of "
                    f"{duplicate_counts[entry_name]})"
                )
            entry_labels[entry["id"]] = (
                f'{entry["meal_type"]}: {entry["food"]}{duplicate_label} — '
                f'{entry["calories"]:g} calories'
            )
        selected_entry_ids = st.multiselect(
            "Select entries to delete",
            options=list(entry_labels),
            format_func=entry_labels.get,
            placeholder="Choose one or more entries",
        )
        if st.button(
            "Delete selected entries",
            disabled=not selected_entry_ids,
            type="secondary",
        ):
            deleted_count = db.delete_entries(selected_entry_ids, user_id)
            st.session_state["entry_message"] = (
                f"Deleted {deleted_count} "
                f'{"entry" if deleted_count == 1 else "entries"}.'
            )
            st.rerun()

    for entry in entries:
        entry_id = entry["id"]
        label = (
            f'{entry["meal_type"]}: {entry["food"]} — '
            f'{entry["calories"]:g} calories'
        )
        with st.expander(label):
            with st.form(f"edit_entry_{entry_id}"):
                edited_date = st.date_input(
                    "Date",
                    value=calendar_date.fromisoformat(entry["date"]),
                    key=f"edit_date_{entry_id}",
                )
                edited_food = st.text_input(
                    "Food",
                    value=entry["food"],
                    key=f"edit_food_{entry_id}",
                )
                current_meal_type = (
                    entry["meal_type"]
                    if entry["meal_type"] in MEAL_TYPES
                    else MEAL_TYPES[0]
                )
                edited_meal_type = st.selectbox(
                    "Meal category",
                    MEAL_TYPES,
                    index=MEAL_TYPES.index(current_meal_type),
                    key=f"edit_meal_type_{entry_id}",
                )
                edited_calories = st.number_input(
                    "Calories",
                    min_value=0.0,
                    value=float(entry["calories"]),
                    step=1.0,
                    key=f"edit_calories_{entry_id}",
                )
                edited_protein = st.number_input(
                    "Protein",
                    min_value=0.0,
                    value=float(entry["protein"]),
                    step=0.1,
                    key=f"edit_protein_{entry_id}",
                )
                edited_carbs = st.number_input(
                    "Carbs",
                    min_value=0.0,
                    value=float(entry["carbs"]),
                    step=0.1,
                    key=f"edit_carbs_{entry_id}",
                )
                edited_fat = st.number_input(
                    "Fat",
                    min_value=0.0,
                    value=float(entry["fat"]),
                    step=0.1,
                    key=f"edit_fat_{entry_id}",
                )
                save_changes = st.form_submit_button("Save changes")

            if save_changes:
                if not edited_food.strip():
                    st.error("The food name cannot be empty.")
                else:
                    updated_entry = {
                        **entry,
                        "date": edited_date.isoformat(),
                        "food": edited_food.strip(),
                        "meal_type": edited_meal_type,
                        "calories": edited_calories,
                        "protein": edited_protein,
                        "carbs": edited_carbs,
                        "fat": edited_fat,
                    }
                    db.update_entry(entry_id, updated_entry, user_id)
                    st.session_state["entry_message"] = "Entry updated."
                    st.rerun()

            if st.button(
                "Delete entry",
                key=f"delete_entry_{entry_id}",
                type="secondary",
            ):
                db.delete_entry(entry_id, user_id)
                st.session_state["entry_message"] = "Entry deleted."
                st.rerun()
