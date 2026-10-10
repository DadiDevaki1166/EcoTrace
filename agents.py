"""CrewAI agents, tasks and crew for the EcoTrace sequential pipeline."""
from __future__ import annotations

import os

from crewai import Agent, Crew, LLM, Process, Task
from crewai.tools import tool

import crewai.llms.cache as crew_cache
crew_cache.mark_cache_breakpoint = lambda msg: msg

from .calculator import ELECTRICITY_FACTOR, FUEL_FACTOR, co2e_kg

MODEL = "groq/openai/gpt-oss-120b"


@tool("carbon_calculator")
def carbon_calculator(kwh: float, liters: float) -> str:
    """Compute total CO2e in kg for given electricity (kWh) and fuel (litres).
    Uses 0.85 kg CO2/kWh and 2.68 kg CO2/litre. Always use this tool for arithmetic."""
    kwh, liters = float(kwh), float(liters)
    return (
        f"Electricity: {kwh} kWh x {ELECTRICITY_FACTOR} = {kwh * ELECTRICITY_FACTOR:.2f} kg CO2 | "
        f"Fuel: {liters} L x {FUEL_FACTOR} = {liters * FUEL_FACTOR:.2f} kg CO2 | "
        f"TOTAL = {co2e_kg(kwh, liters):.2f} kg CO2e"
    )


def build_llm(api_key: str | None = None) -> LLM:
    key = api_key or os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY is not set.")
    return LLM(
    model=MODEL,
    api_key=key,
    temperature=0.1,
    is_litellm=True,
    provider="groq",
)


def build_crew(csv_text: str, api_key: str | None = None) -> Crew:
    llm = build_llm(api_key)

    extractor = Agent(
        role="Data Extraction Specialist",
        goal="Extract accurate electricity (kWh) and fuel (litres) totals per department from raw CSV data.",
        backstory="A meticulous data analyst who never guesses numbers and only reports what is in the file.",
        llm=llm, allow_delegation=False, verbose=True,
    )
    accountant = Agent(
        role="Carbon Accounting Specialist",
        goal="Convert consumption into CO2e using the fixed emission factors, with zero arithmetic errors.",
        backstory=(
            "A GHG accounting expert. Fixed factors: 1 kWh = 0.85 kg CO2; 1 litre fuel = 2.68 kg CO2. "
            "Formula: Total CO2e (kg) = (kWh x 0.85) + (litres x 2.68). Always calls the carbon_calculator tool."
        ),
        tools=[carbon_calculator], llm=llm, allow_delegation=False, verbose=True,
    )
    consultant = Agent(
        role="Sustainability Consultant",
        goal="Identify the primary carbon hotspot and give three practical, specific reduction strategies.",
        backstory="A corporate sustainability advisor who writes clear, actionable audit reports for managers.",
        llm=llm, allow_delegation=False, verbose=True,
    )

    t1 = Task(
        description=(
            "Parse this energy CSV and compute, for each Department, the total Electricity_kWh and "
            "total Fuel_Liters (sum all rows of that department).\n\nCSV DATA:\n" + csv_text
        ),
        expected_output="A markdown table: Department | Total kWh | Total Fuel (litres).",
        agent=extractor,
    )
    t2 = Task(
        description=(
            "Using the extracted table, calculate emissions for every department and the organisation total. "
            "Call carbon_calculator for each department. Show electricity CO2, fuel CO2 and total CO2e (kg)."
        ),
        expected_output="A markdown table: Department | Electricity CO2 (kg) | Fuel CO2 (kg) | Total CO2e (kg), plus a grand total row.",
        agent=accountant, context=[t1],
    )
    t3 = Task(
        description=(
            "Write the final sustainability audit report in Markdown with sections: "
            "1) Executive Summary, 2) Emissions by Department (table), 3) Primary Carbon Hotspot "
            "(department with highest CO2e and its % share), 4) Three Reduction Strategies "
            "(specific to the hotspot's mix of electricity vs fuel), 5) Conclusion. "
            "Use only numbers from the previous step."
        ),
        expected_output="A complete Markdown audit report.",
        agent=consultant, context=[t1, t2],
    )
    return Crew(agents=[extractor, accountant, consultant], tasks=[t1, t2, t3],
                process=Process.sequential, verbose=True)


def run_audit(csv_text: str, api_key: str | None = None) -> str:
    return str(build_crew(csv_text, api_key).kickoff())
