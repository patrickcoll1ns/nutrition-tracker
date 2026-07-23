import os
import streamlit as st
from project import total, make_entry, parse_meal
# No import of save and load because Entries are sessionscoped so they live in st.session_state and die with the browser session.

# Bridge Streamlit Cloud's secrets into the environment so project.py
# can stay streamlit-free and keep reading os.environ.
try:
    os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
except Exception:
    pass

st.title("Nutrition Tracker")

if "entries" not in st.session_state:
    st.session_state["entries"] = []

# Shared by both logging paths, so it has to live above both of them.
date = st.date_input("Date").isoformat()

st.subheader("Describe your meal")
description = st.text_input("What did you eat? ")

if st.button("Parse & log"):
    if not description.strip():
        st.error("Type a meal description first.")
    else: 
        try:
            with st.spinner("Parsing..."):
                parsed = parse_meal(description)
        except Exception:
            # network/quota/key failure — friendly message, NOT a traceback
            parsed = None
            st.error("Couldn't reach the model. Try again, or use the manual form below.")

        if parsed is None:
            pass # error already showed above
        elif not parsed:
            st.warning("I could not find any food in that description.")
        else:
            for item in parsed:
                entry = make_entry(date, item["food"], item["calories"], item["protein"], item["carbs"], item["fat"])
                st.session_state["entries"].append(entry)
            st.success(f"Logged {len(parsed)} item(s).")
        
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
        entry = make_entry(date, food, calories, protein, carbs, fat)
        st.session_state["entries"].append(entry)

total_calories = total(st.session_state["entries"], "calories")
total_protein = total(st.session_state["entries"], "protein")
total_carbs = total(st.session_state["entries"], "carbs")
total_fat = total(st.session_state["entries"], "fat")

st.metric("Calories", total_calories)
st.metric("Protein", total_protein)
st.metric("Carbs", total_carbs)
st.metric("Fat", total_fat)

st.write(st.session_state["entries"])