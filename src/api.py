from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .calculator import (
    build_dashboard_payload,
    calculate_carrier_boxplot,
    calculate_global_baseline,
    calculate_monthly_seasonality,
    calculate_reliability,
    calculate_route_baseline,
)
from .data_loader import load_and_clean_data

app = FastAPI(title="Okos utazastervezo API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

raw_data: Optional[pd.DataFrame] = None
processed_data: Optional[pd.DataFrame] = None
global_baseline: Optional[dict] = None


def _get_route_dataframes(origin: str, dest: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    if raw_data is None or processed_data is None:
        raise HTTPException(status_code=500, detail="Az adatok meg nem toltodtek be.")

    origin_code = origin.upper()
    dest_code = dest.upper()

    route_recommendations = processed_data[
        (processed_data["origin"] == origin_code)
        & (processed_data["dest"] == dest_code)
    ]
    route_raw = raw_data[
        (raw_data["origin"] == origin_code)
        & (raw_data["dest"] == dest_code)
    ]

    if route_recommendations.empty or route_raw.empty:
        raise HTTPException(status_code=404, detail="Nincs adat erre az utvonalra.")

    return route_recommendations, route_raw


@app.on_event("startup")
def startup_event() -> None:
    global raw_data, processed_data, global_baseline

    print("Adatok elokeszitese")
    raw_data = load_and_clean_data()
    processed_data = calculate_reliability(raw_data)
    global_baseline = calculate_global_baseline(raw_data)
    print("Adatok kesz, API keszen all")


@app.get("/recommend")
def get_recommendation(origin: str, dest: str):
    route_recommendations, _ = _get_route_dataframes(origin, dest)
    return route_recommendations.head(5).to_dict(orient="records")


@app.get("/analytics")
def get_analytics(origin: str, dest: str):
    if global_baseline is None:
        raise HTTPException(status_code=500, detail="Az adatok meg nem toltodtek be.")

    _, route_data = _get_route_dataframes(origin, dest)

    return {
        "baseline": calculate_route_baseline(route_data, global_baseline),
        "seasonality": calculate_monthly_seasonality(route_data),
        "carrier_boxplot": calculate_carrier_boxplot(route_data),
    }


@app.get("/dashboard")
def get_dashboard(origin: str, dest: str):
    if global_baseline is None:
        raise HTTPException(status_code=500, detail="Az adatok meg nem toltodtek be.")

    route_recommendations, route_data = _get_route_dataframes(origin, dest)
    recommendations = route_recommendations.head(5).copy()
    baseline = calculate_route_baseline(route_data, global_baseline)
    seasonality = calculate_monthly_seasonality(route_data)
    boxplot = calculate_carrier_boxplot(route_data)

    return build_dashboard_payload(
        recommendations=recommendations,
        baseline=baseline,
        seasonality=seasonality,
        boxplot=boxplot,
    )


@app.get("/airports")
def get_airports():
    if processed_data is None:
        return {"origins": [], "destinations": []}

    return {
        "origins": sorted(processed_data["origin"].unique().tolist()),
        "destinations": sorted(processed_data["dest"].unique().tolist()),
    }
