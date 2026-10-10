# EcoTrace – Agentic Carbon Accounting & Multi-Agent Sustainability Audit System

Upload an energy CSV → three CrewAI agents (Data Extraction → Carbon Accounting → Sustainability Consultant) produce a Markdown audit report with emissions, the main carbon hotspot and three reduction strategies.

**Formula:** `Total CO2e (kg) = (kWh × 0.85) + (litres × 2.68)`

## Setup
```bash
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # then put your Groq key in .env (free key: console.groq.com)
streamlit run app.py
```
Python 3.10–3.12 recommended for CrewAI.

## CSV format
Required columns: `Department`, `Electricity_kWh`, `Fuel_Liters` (optional `Month`). See `sample_data/energy_data.csv`.

## Project layout
| Path | Purpose |
|---|---|
| `app.py` | Streamlit UI (upload, preview, metrics, chart, run audit, download) |
| `ecotrace/agents.py` | 3 agents, 3 sequential tasks, `carbon_calculator` tool, Groq LLM |
| `ecotrace/calculator.py` | Deterministic maths + validation (also cross-checks the agents) |
| `tests/test_calculator.py` | Unit tests (`pytest`) |

## Why it avoids LLM arithmetic errors
Agents call a `carbon_calculator` tool for all maths, and the UI shows an independent pandas-computed table so the agent report can be verified.
