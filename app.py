import os
import traceback
import streamlit as st
from project import total, make_entry, parse_meal, MealLookupError
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

# Shared by both logging paths, so it has to live above both of them.
date = st.date_input("Date").isoformat()

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
                entry = make_entry(date, item["food"], calories=item["calories"], protein=item["protein"],
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
        entry = make_entry(date, food, calories=calories, protein=protein, carbs=carbs, fat=fat,
                            usda_id=None, usda_description=None, grams=None)
        db.save_entry(entry)

entries = db.entries_for(date)
total_calories = total(entries, "calories")
total_protein = total(entries, "protein")
total_carbs = total(entries, "carbs")
total_fat = total(entries, "fat")

st.metric("Calories", total_calories)
st.metric("Protein", total_protein)
st.metric("Carbs", total_carbs)
st.metric("Fat", total_fat)

st.write(entries)
