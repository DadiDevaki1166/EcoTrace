"""EcoTrace - Streamlit front end.  Run:  streamlit run app.py"""
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from ecotrace.calculator import ELECTRICITY_FACTOR, FUEL_FACTOR, summarise, totals

load_dotenv()
st.set_page_config(page_title="EcoTrace", page_icon="🌍", layout="wide")

st.title("🌍 EcoTrace")
st.caption("Agentic Carbon Accounting & Multi-Agent Sustainability Audit System")

with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Groq API key", value=os.getenv("GROQ_API_KEY", ""), type="password")
    st.markdown(
        f"**Emission factors**\n- Electricity: 1 kWh = {ELECTRICITY_FACTOR} kg CO₂\n"
        f"- Fuel: 1 litre = {FUEL_FACTOR} kg CO₂\n\n"
        "`CO₂e = kWh×0.85 + litres×2.68`"
    )
    st.markdown("**CSV columns:** `Department`, `Electricity_kWh`, `Fuel_Liters` (optional `Month`).")

uploaded = st.file_uploader("Upload energy usage CSV", type=["csv"])
use_sample = st.checkbox("Use bundled sample data", value=uploaded is None)

df = None
if uploaded is not None:
    df = pd.read_csv(uploaded)
elif use_sample:
    df = pd.read_csv("sample_data/energy_data.csv")

if df is not None:
    st.subheader("1. Raw data preview")
    st.dataframe(df, use_container_width=True)
    try:
        summary = summarise(df)
    except ValueError as e:
        st.error(str(e))
        st.stop()

    t = totals(summary)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Electricity (kWh)", f"{t['kwh']:,.0f}")
    c2.metric("Fuel (litres)", f"{t['liters']:,.0f}")
    c3.metric("Total CO₂e (kg)", f"{t['co2e_kg']:,.2f}")
    c4.metric("Top hotspot", t["hotspot"])

    st.subheader("2. Verified emissions (deterministic cross-check)")
    st.dataframe(summary, use_container_width=True)
    st.bar_chart(summary.set_index("Department")[["Electricity_CO2e_kg", "Fuel_CO2e_kg"]])

    st.subheader("3. Multi-agent audit report")
    if st.button("🚀 Run EcoTrace audit", type="primary"):
        if not api_key:
            st.error("Enter your Groq API key in the sidebar (or set GROQ_API_KEY in .env).")
        else:
            from ecotrace.agents import run_audit  # imported lazily: heavy

            with st.spinner("Agents are working: Extraction → Accounting → Consulting..."):
                try:
                    report = run_audit(df.to_csv(index=False), api_key)
                except Exception as e:  # surface API / network errors cleanly
                    st.error(f"Audit failed: {e}")
                    st.stop()
            st.markdown(report)
            st.download_button("Download report (.md)", report, "ecotrace_audit.md", "text/markdown")
            st.info(f"Cross-check: verified organisation total = **{t['co2e_kg']:,.2f} kg CO₂e**. "
                    "Compare with the agent's figure above.")
else:
    st.info("Upload a CSV or tick the sample-data box to begin.")
