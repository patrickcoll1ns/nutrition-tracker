import streamlit as st
from project import total, make_entry

st.title("nutrition tracker")
st.write("Log foods")

if "entries" not in st.session_state:
    st.session_state["entries"] = []

date = st.text_input("Date")
food = st.text_input("Food")
calories = st.number_input("Calories", min_value=0, step=1)
protein = st.number_input("Protein", min_value=0.0, step=0.1)
carbs = st.number_input("Carbs", min_value=0.0, step=0.1)
fat = st.number_input("Fat", min_value=0.0, step=0.1)

if st.button("Make Entry"):
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