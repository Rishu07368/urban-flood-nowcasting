from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from backend.flood_engine import assess_zone_risk, summarize_risk
from backend.sensors import SimulatedSensorSource
from extract_result import extract_swmm_results
from run_simulation import RAIN_FILE, load_rainfall, run_swmm, update_swmm_rainfall

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FILE = ROOT / "swmm" / "flood_output.out"

TIME_LABELS = [
    {"minutes": 0, "label": "NOW"},
    {"minutes": 30, "label": "+30m"},
    {"minutes": 60, "label": "+1h"},
    {"minutes": 90, "label": "+1.5h"},
    {"minutes": 120, "label": "+2h"},
    {"minutes": 150, "label": "+2.5h"},
    {"minutes": 180, "label": "+3h"},
]

ZONES: List[Dict[str, Any]] = [
    {
        "zone_id": "ZONE_01",
        "node": "J1",
        "link": "C1",
        "geometry": [[76.760, 30.680], [76.820, 30.680], [76.820, 30.740], [76.760, 30.740]],
    },
    {
        "zone_id": "ZONE_02",
        "node": "J2",
        "link": "C2",
        "geometry": [[76.790, 30.700], [76.860, 30.700], [76.860, 30.760], [76.790, 30.760]],
    },
    {
        "zone_id": "ZONE_03",
        "node": "J3",
        "link": "C3",
        "geometry": [[76.820, 30.720], [76.890, 30.720], [76.890, 30.780], [76.820, 30.780]],
    },
    {
        "zone_id": "ZONE_04",
        "node": "J2",
        "link": "C2",
        "geometry": [[76.760, 30.760], [76.820, 30.760], [76.820, 30.820], [76.760, 30.820]],
    },
    {
        "zone_id": "ZONE_05",
        "node": "J3",
        "link": "C3",
        "geometry": [[76.820, 30.780], [76.890, 30.780], [76.890, 30.840], [76.820, 30.840]],
    },
]

_risk_states_cache: tuple[int, List[Dict[str, Any]]] | None = None


def _get_rainfall_value(rainfall_forecast: List[Dict[str, Any]], minutes_from_now: int) -> float:
    if not rainfall_forecast:
        return 0.0
    minute_slots = [0, 30, 60, 90, 120, 150, 180]
    target = max(0, min(180, minutes_from_now))
    if target in minute_slots:
        index = minute_slots.index(target)
        return float(rainfall_forecast[index]["rainfall_mm_hr"])

    for idx in range(len(minute_slots) - 1):
        left, right = minute_slots[idx], minute_slots[idx + 1]
        if left <= target <= right:
            left_val = float(rainfall_forecast[idx]["rainfall_mm_hr"])
            right_val = float(rainfall_forecast[idx + 1]["rainfall_mm_hr"])
            ratio = (target - left) / (right - left)
            return left_val + (right_val - left_val) * ratio
    return float(rainfall_forecast[-1]["rainfall_mm_hr"])


def _extract_series(metrics: Dict[str, Any], minutes_from_now: int) -> float:
    if not metrics:
        return 0.0
    time_map = []
    for key in metrics:
        dt = datetime.fromisoformat(key)
        delta_minutes = int((dt - datetime(2026, 9, 4, 0, 0)).total_seconds() / 60)
        time_map.append((delta_minutes, float(metrics[key])))
    if not time_map:
        return 0.0
    nearest = min(time_map, key=lambda item: abs(item[0] - minutes_from_now))
    return float(nearest[1])


def _get_zone_metrics(swmm_results: Dict[str, Any], zone: Dict[str, Any], forecast_minutes: int) -> Tuple[float, float, float, float]:
    node = zone["node"]
    link = zone["link"]
    node_metrics = swmm_results.get("nodes", {}).get(node, {})
    link_metrics = swmm_results.get("links", {}).get(link, {})
    depth = _extract_series(node_metrics.get("invert_depth", {}), forecast_minutes)
    predicted_level = depth
    flow = _extract_series(link_metrics.get("flow_rate", {}), forecast_minutes)
    flood_losses = _extract_series(node_metrics.get("flooding_losses", {}), forecast_minutes)
    return depth, predicted_level, flow, flood_losses


def _sensor_observed_level(sensor_payload: Dict[str, Any], zone_id: str, forecast_minutes: int) -> float:
    sensor_map = {
        "ZONE_01": "DRAIN_001",
        "ZONE_02": "DRAIN_002",
        "ZONE_03": "DRAIN_003",
        "ZONE_04": "DRAIN_002",
        "ZONE_05": "DRAIN_003",
    }
    sensor_id = sensor_map.get(zone_id, "DRAIN_001")
    readings = sensor_payload.get("water_levels", [])
    for reading in readings:
        if reading.get("sensor_id") == sensor_id:
            if reading.get("timestamp"):
                ts = datetime.fromisoformat(reading["timestamp"])
                if abs(int((ts - datetime(2026, 9, 4, 0, 0)).total_seconds() / 60) - forecast_minutes) <= 10:
                    return float(reading["value"])
            return float(reading["value"])
    return 0.0


def generate_risk_states() -> List[Dict[str, Any]]:
    global _risk_states_cache

    rainfall_file_mtime = RAIN_FILE.stat().st_mtime_ns
    if _risk_states_cache is not None and _risk_states_cache[0] == rainfall_file_mtime:
        return _risk_states_cache[1]

    rainfall_payload = load_rainfall()
    update_swmm_rainfall(rainfall_payload)
    run_swmm()
    swmm_results = extract_swmm_results(OUTPUT_FILE)
    simulated = SimulatedSensorSource()
    sensor_payload = {"rainfall": simulated.rainfall_readings(), "water_levels": simulated.water_level_readings()}

    risk_states: List[Dict[str, Any]] = []
    for entry in TIME_LABELS:
        forecast_minutes = entry["minutes"]
        rainfall_value = _get_rainfall_value(rainfall_payload["rainfall_forecast"], forecast_minutes)
        zone_results = []
        for zone in ZONES:
            depth, predicted_level, flow, flooding_losses = _get_zone_metrics(swmm_results, zone, forecast_minutes)
            sensor_observed = _sensor_observed_level(sensor_payload, zone["zone_id"], forecast_minutes)
            if not sensor_observed:
                sensor_observed = max(0.0, predicted_level * 0.85 + 0.04)
            rate_of_rise = 0.0
            if forecast_minutes > 0:
                previous_depth = _get_zone_metrics(swmm_results, zone, max(0, forecast_minutes - 30))[0]
                rate_of_rise = max(0.0, depth - previous_depth) / 0.5

            zone_result = assess_zone_risk(
                zone_id=zone["zone_id"],
                water_depth_m=depth,
                rainfall_mm_hr=rainfall_value,
                flow_rate_cms=flow,
                observed_level_m=sensor_observed,
                predicted_level_m=predicted_level,
                rate_of_rise_m_per_hr=rate_of_rise,
            )
            zone_result["geometry"] = zone["geometry"]
            zone_result["flooding_losses"] = round(flooding_losses, 3)
            zone_results.append(zone_result)

        summary = summarize_risk(zone_results)
        risk_states.append(
            {
                "forecast_minutes": forecast_minutes,
                "forecast_label": entry["label"],
                "risk_summary": summary,
                "zones": zone_results,
            }
        )

    _risk_states_cache = (rainfall_file_mtime, risk_states)
    return risk_states


def build_geojson_for_time(forecast_minutes: int) -> Dict[str, Any]:
    states = generate_risk_states()
    selected = next((state for state in states if state["forecast_minutes"] == forecast_minutes), states[0])
    features = []
    for zone in selected["zones"]:
        geometry = {"type": "Polygon", "coordinates": [[list(point) for point in zone["geometry"]]]}
        feature = {
            "type": "Feature",
            "properties": {
                "zone_id": zone["zone_id"],
                "risk_score": zone["risk_score"],
                "risk_category": zone["risk_category"],
                "water_depth_m": zone["water_depth_m"],
                "forecast_time": selected["forecast_label"],
                "warning": "MODEL/SENSOR DEVIATION DETECTED" if zone["model_sensor_deviation_detected"] else "within expected model bounds",
            },
            "geometry": geometry,
        }
        features.append(feature)
    return {"type": "FeatureCollection", "features": features, "summary": selected["risk_summary"]}


def build_risk_snapshot_for_label(label: str) -> Dict[str, Any]:
    normalized = str(label or "NOW").strip().replace(" ", "")
    lookup = {item["label"]: item["minutes"] for item in TIME_LABELS}
    lookup.update({
        "30m": 30,
        "1h": 60,
        "1.5h": 90,
        "2h": 120,
        "2.5h": 150,
        "3h": 180,
        "+30m": 30,
        "+1h": 60,
        "+1.5h": 90,
        "+2h": 120,
        "+2.5h": 150,
        "+3h": 180,
    })
    if normalized.startswith("+"):
        normalized = normalized[1:]
        if normalized in {"30m", "1h", "1.5h", "2h", "2.5h", "3h"}:
            return build_geojson_for_time(lookup.get(f"+{normalized}", lookup.get(normalized, 0)))
    time_minutes = lookup.get(normalized, lookup.get(f"+{normalized}", 0))
    return build_geojson_for_time(time_minutes)
