from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from extract_result import extract_swmm_results
from run_simulation import OUTPUT_FILE, load_rainfall, run_swmm, update_swmm_rainfall


def run_full_pipeline() -> Dict[str, Any]:
    rainfall = load_rainfall()
    update_swmm_rainfall(rainfall)
    run_swmm()
    results = extract_swmm_results(OUTPUT_FILE)
    return {
        "status": "success",
        "rainfall_points": len(rainfall.get("rainfall_forecast", [])),
        "output_file": str(OUTPUT_FILE),
        "node_count": len(results.get("nodes", {})),
        "link_count": len(results.get("links", {})),
        "summary": {
            "nodes": list(results.get("nodes", {}).keys()),
            "links": list(results.get("links", {}).keys()),
        },
    }
