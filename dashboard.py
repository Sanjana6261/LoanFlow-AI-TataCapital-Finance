import streamlit as st
import pandas as pd

st.title("Analytics Dashboard")
df = pd.DataFrame({
    'Date': pd.date_range(start='2025-12-01', periods=7),
    'Conversions': [80, 85, 90, 95, 100, 110, 120]
})
st.line_chart(df.set_index('Date'))
st.caption("7-day trend – 25% uplift from AI bot!")