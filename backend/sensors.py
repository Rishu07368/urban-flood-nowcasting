from __future__ import annotations

import json
import math
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
RAIN_FILE = ROOT / "data" / "rainfall_nowcast.json"


class SensorSource(ABC):
    @abstractmethod
    def rainfall_readings(self) -> List[Dict[str, Any]]:
        """Return rainfall observations as common sensor payloads."""

    @abstractmethod
    def water_level_readings(self) -> List[Dict[str, Any]]:
        """Return drainage/water-level observations as common sensor payloads."""


class SimulatedSensorSource(SensorSource):
    """Deterministic software sensor simulator for the SIH prototype."""

    def __init__(self, rainfall_file: Path | str = RAIN_FILE):
        self.rainfall_file = Path(rainfall_file)

    def _load_rainfall_forecast(self) -> List[Dict[str, Any]]:
        with self.rainfall_file.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return payload.get("rainfall_forecast", [])

    def rainfall_readings(self) -> List[Dict[str, Any]]:
        forecast = self._load_rainfall_forecast()
        sensor_positions = [
            {"sensor_id": "RAIN_001", "lat": 30.700, "lon": 76.800},
            {"sensor_id": "RAIN_002", "lat": 30.710, "lon": 76.820},
            {"sensor_id": "RAIN_003", "lat": 30.720, "lon": 76.790},
        ]

        readings: List[Dict[str, Any]] = []
        base_dt = datetime(2026, 9, 4, 0, 0)
        for idx, item in enumerate(forecast):
            rainfall_value = float(item["rainfall_mm_hr"])
            timestamp = (base_dt + timedelta(minutes=30 * idx)).isoformat(timespec="minutes")
            for sensor_index, position in enumerate(sensor_positions):
                variation = 1.0 + 0.12 * math.sin((idx + 1) * (sensor_index + 1))
                value = max(0.0, rainfall_value * variation)
                readings.append(
                    {
                        "sensor_id": position["sensor_id"],
                        "type": "rainfall",
                        "location": {"lat": position["lat"], "lon": position["lon"]},
                        "value": round(value, 2),
                        "unit": "mm/hr",
                        "timestamp": timestamp,
                        "source": "simulated",
                        "station_name": "Prototype rainfall sensor",
                    }
                )
        return readings

    def water_level_readings(self) -> List[Dict[str, Any]]:
        forecast = self._load_rainfall_forecast()
        sensor_positions = [
            {"sensor_id": "DRAIN_001", "lat": 30.700, "lon": 76.800},
            {"sensor_id": "DRAIN_002", "lat": 30.710, "lon": 76.820},
            {"sensor_id": "DRAIN_003", "lat": 30.720, "lon": 76.790},
        ]

        readings: List[Dict[str, Any]] = []
        base_dt = datetime(2026, 9, 4, 0, 0)
        for idx, item in enumerate(forecast):
            rainfall_value = float(item["rainfall_mm_hr"])
            timestamp = (base_dt + timedelta(minutes=30 * idx)).isoformat(timespec="minutes")
            for sensor_index, position in enumerate(sensor_positions):
                base_level = 0.12 + (rainfall_value * 0.0045)
                dynamic_component = 0.04 * sensor_index
                noise = 0.02 * math.sin(idx * (sensor_index + 1))
                value = max(0.0, base_level + dynamic_component + noise)
                readings.append(
                    {
                        "sensor_id": position["sensor_id"],
                        "type": "water_level",
                        "location": {"lat": position["lat"], "lon": position["lon"]},
                        "value": round(value, 3),
                        "unit": "m",
                        "timestamp": timestamp,
                        "source": "simulated",
                        "station_name": "Prototype drainage sensor",
                    }
                )
        return readings


class RealSensorSource(SensorSource):
    """Placeholder adapter for future real IoT/HTTP/MQTT integrations."""

    def rainfall_readings(self) -> List[Dict[str, Any]]:
        raise NotImplementedError("Real rainfall sensor adapter is not connected in this prototype.")

    def water_level_readings(self) -> List[Dict[str, Any]]:
        raise NotImplementedError("Real drainage sensor adapter is not connected in this prototype.")


def build_sensor_payload() -> Dict[str, Any]:
    source = SimulatedSensorSource()
    return {
        "simulated": True,
        "caption": "Sensor values are simulated for this SIH prototype. Real IoT sensors can replace this adapter without changing the API contract.",
        "rainfall": source.rainfall_readings(),
        "water_levels": source.water_level_readings(),
    }
