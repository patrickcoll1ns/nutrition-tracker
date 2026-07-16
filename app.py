import streamlit as st
from project import total, make_entry, load, save

st.title("nutrition tracker")
st.write("Log foods")

if "entries" not in st.session_state:
    st.session_state["entries"] = []
