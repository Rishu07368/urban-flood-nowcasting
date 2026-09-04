from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.risk_mapper import build_risk_snapshot_for_label, generate_risk_states
from backend.sensors import build_sensor_payload
from backend.simulation import run_full_pipeline

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT / "frontend"

app = FastAPI(title="Urban Flood Nowcasting Prototype")

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
def serve_frontend() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "urban-flood-nowcasting", "message": "Backend is running."}


@app.get("/api/sensors")
def sensors() -> dict:
    return build_sensor_payload()


@app.get("/api/rainfall")
def rainfall() -> dict:
    from run_simulation import load_rainfall

    return {"source": "synthetic IMD-style nowcast", "synthetic": True, "data": load_rainfall()}


@app.get("/api/water-levels")
def water_levels() -> dict:
    payload = build_sensor_payload()
    return {"source": "simulated", "synthetic": True, "data": payload["water_levels"]}


@app.get("/api/simulation")
def simulation() -> dict:
    try:
        return run_full_pipeline()
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/flood-risk")
def flood_risk() -> dict:
    try:
        return {"source": "swmm + simulated sensors", "states": generate_risk_states()}
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/flood-map")
def flood_map(time: str = "NOW") -> dict:
    try:
        label = (time or "NOW").strip().replace(" ", "")
        if not label:
            label = "NOW"
        if label == "+":
            label = "NOW"
        return build_risk_snapshot_for_label(label)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc
