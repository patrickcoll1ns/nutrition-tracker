import os
import traceback
from collections import Counter, defaultdict
from datetime import date as calendar_date
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

# Bridge Streamlit Cloud's secrets into the environment so project.py
# can stay streamlit-free and keep reading os.environ.
try:
    os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
    os.environ["USDA_API_KEY"] = st.secrets["USDA_API_KEY"]
except Exception:
    pass

st.title("Nutrition Tracker")

db.init_db()

if "entry_message" in st.session_state:
    st.success(st.session_state.pop("entry_message"))

# Shared by both logging paths, so it has to live above both of them.
date = st.date_input("Date").isoformat()
meal_type = st.selectbox("Meal category", MEAL_TYPES)

st.subheader("Describe your meal")
description = st.text_input("What did you eat? ", max_chars=300)

if st.button("Parse & log"):
    if not description.strip():
        st.error("Type a meal description first.")
    else: 
        parsed, unmatched = None, []
        try:
            with st.spinner("Parsing..."):
                parsed, unmatched = parse_meal(description)
        except MealLookupError as e:
            # Message is pre-sanitized in project.py — safe to show as-is,
            # and it correctly identifies which service (Claude vs USDA) failed.
            st.error(str(e))
        except Exception:
            # Anything else is an unexpected bug, not a network/API issue.
            # Don't show the raw exception text to end users; log it instead.
            st.error("Something went wrong parsing that meal. Try again, or use the manual form below.")
            traceback.print_exc()

        if parsed is None:
            pass # error already showed above
        elif not parsed and not unmatched:
            st.warning("I could not find any food in that description.")
        else:
            for item in parsed:
                entry = make_entry(date, item["food"], meal_type=meal_type,
                                    calories=item["calories"], protein=item["protein"],
                                    carbs=item["carbs"], fat=item["fat"], usda_id=item["usda_id"],
                                    usda_description=item["usda_description"], grams=item["grams"])
                db.save_entry(entry)
            if parsed:
                st.success(f"Logged {len(parsed)} item(s).")
            if unmatched:
                st.warning(f"Couldn't find a USDA match for: {', '.join(unmatched)} — not logged.")
        
st.subheader("Or enter it manually")

with st.form("entry_form", clear_on_submit=True):   
    food = st.text_input("Food")
    calories = st.number_input("Calories", min_value=0, step=1)
    protein = st.number_input("Protein", min_value=0.0, step=0.1)
    carbs = st.number_input("Carbs", min_value=0.0, step=0.1)
    fat = st.number_input("Fat", min_value=0.0, step=0.1)
    submitted = st.form_submit_button("Make Entry")    

if submitted:
    if not food.strip():
        st.error("Enter a food name before making an entry.")
    else:
        entry = make_entry(date, food, meal_type=meal_type, calories=calories,
                            protein=protein, carbs=carbs, fat=fat,
                            usda_id=None, usda_description=None, grams=None)
        db.save_entry(entry)

entries = db.entries_with_ids_for(date)
total_calories = total(entries, "calories")
total_protein = total(entries, "protein")
total_carbs = total(entries, "carbs")
total_fat = total(entries, "fat")

metric_columns = st.columns(4)
metric_columns[0].metric("Calories", total_calories)
metric_columns[1].metric("Protein", total_protein)
metric_columns[2].metric("Carbs", total_carbs)
metric_columns[3].metric("Fat", total_fat)

st.subheader("Nutrition trends")
averages = db.averages_for_current_period()
st.caption(
    f'Average across {averages["days_logged"]} logged day(s) since the '
    "last reset. Days without logs are not included."
)

average_columns = st.columns(4)
average_columns[0].metric("Average calories", averages["calories"])
average_columns[1].metric("Average protein", averages["protein"])
average_columns[2].metric("Average carbs", averages["carbs"])
average_columns[3].metric("Average fat", averages["fat"])

trend_action_columns = st.columns(2)
if trend_action_columns[0].button(
    "Analyze trends with AI",
    disabled=averages["days_logged"] == 0,
):
    try:
        with st.spinner("Analyzing your logged trends..."):
            st.session_state["trend_analysis"] = analyze_nutrition_trends(
                db.daily_totals_for_current_period()
            )
    except MealLookupError as e:
        st.error(str(e))

if trend_action_columns[1].button("Reset averages"):
    db.reset_averages()
    st.session_state.pop("trend_analysis", None)
    st.session_state["entry_message"] = (
        "A new averaging period has started. Your food logs were not deleted."
    )
    st.rerun()

if "trend_analysis" in st.session_state:
    st.write(st.session_state["trend_analysis"])

st.subheader("Entries for selected date")

if not entries:
    st.info("No entries logged for this date.")
else:
    entry_names = [
        (
            entry["meal_type"],
            entry["food"],
            entry["calories"],
        )
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
        deleted_count = db.delete_entries(selected_entry_ids)
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
                db.update_entry(entry_id, updated_entry)
                st.session_state["entry_message"] = "Entry updated."
                st.rerun()

        if st.button(
            "Delete entry",
            key=f"delete_entry_{entry_id}",
            type="secondary",
        ):
            db.delete_entry(entry_id)
            st.session_state["entry_message"] = "Entry deleted."
            st.rerun()
