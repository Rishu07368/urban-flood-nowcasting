from __future__ import annotations

from typing import Any, Dict, List

RISK_LEVELS = [
    {"name": "SAFE", "min": 0, "max": 20, "color": "#2ecc71"},
    {"name": "LOW", "min": 21, "max": 40, "color": "#f1c40f"},
    {"name": "MODERATE", "min": 41, "max": 60, "color": "#f39c12"},
    {"name": "HIGH", "min": 61, "max": 80, "color": "#e74c3c"},
    {"name": "CRITICAL", "min": 81, "max": 100, "color": "#8e44ad"},
]


def classify_risk(score: float) -> str:
    score = max(0, min(100, float(score)))
    for band in RISK_LEVELS:
        if band["min"] <= score <= band["max"]:
            return band["name"]
    return "SAFE"


def category_color(category: str) -> str:
    for band in RISK_LEVELS:
        if band["name"] == category:
            return band["color"]
    return "#2ecc71"


def assess_zone_risk(
    zone_id: str,
    water_depth_m: float,
    rainfall_mm_hr: float,
    flow_rate_cms: float,
    observed_level_m: float,
    predicted_level_m: float,
    rate_of_rise_m_per_hr: float,
) -> Dict[str, Any]:
    deviation_m = observed_level_m - predicted_level_m
    depth_component = min(water_depth_m * 70.0, 40.0)
    rainfall_component = min(rainfall_mm_hr * 0.25, 25.0)
    flow_component = min(flow_rate_cms * 45.0, 20.0)
    deviation_component = min(abs(deviation_m) * 180.0, 15.0)
    rise_component = min(max(0.0, rate_of_rise_m_per_hr) * 35.0, 10.0)

    score = depth_component + rainfall_component + flow_component + deviation_component + rise_component
    score = max(0.0, min(100.0, score))
    risk_score = round(score)
    risk_category = classify_risk(risk_score)

    return {
        "zone_id": zone_id,
        "risk_score": risk_score,
        "risk_category": risk_category,
        "risk_color": category_color(risk_category),
        "water_depth_m": round(water_depth_m, 3),
        "rainfall_mm_hr": round(rainfall_mm_hr, 2),
        "flow_rate_cms": round(flow_rate_cms, 3),
        "predicted_level_m": round(predicted_level_m, 3),
        "observed_level_m": round(observed_level_m, 3),
        "deviation_m": round(deviation_m, 3),
        "model_sensor_deviation_detected": abs(deviation_m) > 0.08,
        "rate_of_rise_m_per_hr": round(rate_of_rise_m_per_hr, 3),
        "components": {
            "depth": round(depth_component, 2),
            "rainfall": round(rainfall_component, 2),
            "flow": round(flow_component, 2),
            "deviation": round(deviation_component, 2),
            "rise": round(rise_component, 2),
        },
    }


def summarize_risk(zones: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not zones:
        return {"affected_zones": 0, "highest_risk_zone": "N/A", "max_risk_score": 0, "max_depth_m": 0.0}

    highest = max(zones, key=lambda item: item["risk_score"])
    affected = sum(1 for item in zones if item["risk_score"] >= 21)
    max_depth = max(item["water_depth_m"] for item in zones)
    return {
        "affected_zones": affected,
        "highest_risk_zone": highest["zone_id"],
        "max_risk_score": highest["risk_score"],
        "max_depth_m": round(max_depth, 3),
    }
