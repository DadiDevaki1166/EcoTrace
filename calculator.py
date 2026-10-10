"""Deterministic carbon maths.

The LLM never does arithmetic: all numbers come from this module, which is
exposed to the agents as a tool and also used by the UI to cross-check the
final report.
"""
from __future__ import annotations

import pandas as pd

# Fixed conversion factors used by the project (kg CO2 per unit)
ELECTRICITY_FACTOR = 0.85   # kg CO2 per kWh
FUEL_FACTOR = 2.68          # kg CO2 per litre of fuel

REQUIRED_COLUMNS = ["Department", "Electricity_kWh", "Fuel_Liters"]


def co2e_kg(kwh: float, liters: float) -> float:
    """Total CO2e (kg) = (kWh x 0.85) + (litres x 2.68)."""
    return round(kwh * ELECTRICITY_FACTOR + liters * FUEL_FACTOR, 2)


def validate(df: pd.DataFrame) -> pd.DataFrame:
    """Check columns, coerce numerics, drop unusable rows."""
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"CSV is missing required column(s): {', '.join(missing)}. "
            f"Expected at least: {', '.join(REQUIRED_COLUMNS)}"
        )
    for col in ("Electricity_kWh", "Fuel_Liters"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["Department"])
    df[["Electricity_kWh", "Fuel_Liters"]] = df[["Electricity_kWh", "Fuel_Liters"]].fillna(0)
    if (df[["Electricity_kWh", "Fuel_Liters"]] < 0).any().any():
        raise ValueError("Negative consumption values found in the CSV.")
    return df


def summarise(df: pd.DataFrame) -> pd.DataFrame:
    """Per-department totals with emissions and share of total."""
    df = validate(df)
    g = df.groupby("Department", as_index=False)[["Electricity_kWh", "Fuel_Liters"]].sum()
    g["Electricity_CO2e_kg"] = (g["Electricity_kWh"] * ELECTRICITY_FACTOR).round(2)
    g["Fuel_CO2e_kg"] = (g["Fuel_Liters"] * FUEL_FACTOR).round(2)
    g["Total_CO2e_kg"] = (g["Electricity_CO2e_kg"] + g["Fuel_CO2e_kg"]).round(2)
    total = g["Total_CO2e_kg"].sum()
    g["Share_%"] = (g["Total_CO2e_kg"] / total * 100).round(1) if total else 0.0
    return g.sort_values("Total_CO2e_kg", ascending=False).reset_index(drop=True)


def totals(summary: pd.DataFrame) -> dict:
    return {
        "kwh": float(summary["Electricity_kWh"].sum()),
        "liters": float(summary["Fuel_Liters"].sum()),
        "co2e_kg": round(float(summary["Total_CO2e_kg"].sum()), 2),
        "hotspot": summary.iloc[0]["Department"] if len(summary) else None,
    }
