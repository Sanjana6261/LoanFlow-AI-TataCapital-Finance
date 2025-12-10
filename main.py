import streamlit as st
from master_agent import run
from dotenv import load_dotenv
import os

load_dotenv()

st.set_page_config(page_title="LoanFlow AI", layout="wide")
st.title("🏦 Tata Capital LoanFlow AI")
st.caption("Chat for instant personal loan – AI powered!")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Input
if prompt := st.chat_input("Hi! How much loan do you need?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Processing loan request..."):
            response = run(prompt, st.session_state.messages)
        st.write(response)
    st.session_state.messages.append({"role": "assistant", "content": response})

# Sidebar Dashboard
with st.sidebar:
    st.header("📊 Live Dashboard")
    st.metric("Conversion Rate", "89%", " +5%")
    st.metric("Avg Approval Time", "3.2 min", " -1 min")
    st.bar_chart({"Approvals": [100, 120, 150], "Rejects": [10, 8, 5]})