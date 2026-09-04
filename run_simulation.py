import json
from pathlib import Path
from shutil import copy2

from pyswmm import Simulation

ROOT = Path(__file__).resolve().parent
RAIN_FILE = ROOT / "data" / "rainfall_nowcast.json"
BASE_INP = ROOT / "swmm" / "urban_flood.inp"
GENERATED_INP = ROOT / "swmm" / "generated_flood_model.inp"
REPORT_FILE = ROOT / "swmm" / "flood_report.rpt"
OUTPUT_FILE = ROOT / "swmm" / "flood_output.out"


def load_rainfall():
    with RAIN_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def update_swmm_rainfall(data):
    BASE_INP.parent.mkdir(parents=True, exist_ok=True)
    copy2(BASE_INP, GENERATED_INP)

    rainfall = data.get("rainfall_forecast")
    if not rainfall:
        raise ValueError("Rainfall forecast is empty or missing.")

    with GENERATED_INP.open("r", encoding="utf-8") as f:
        content = f.read()

    start = content.index("[TIMESERIES]")
    end = content.find("\n[", start + 1)
    if end == -1:
        end = len(content)

    timeseries = "[TIMESERIES]\n"
    timeseries += ";;Name   Date        Time     Value\n"
    for item in rainfall:
        timeseries += (
            f"STORM    09/04/2026  "
            f"{item['time']}    "
            f"{item['rainfall_mm_hr']}\n"
        )

    content = content[:start] + timeseries + content[end:]
    with GENERATED_INP.open("w", encoding="utf-8") as f:
        f.write(content)


def run_swmm():
    print("Starting SWMM simulation...")
    with Simulation(
        str(GENERATED_INP),
        reportfile=str(REPORT_FILE),
        outputfile=str(OUTPUT_FILE),
    ) as sim:
        sim.start()
        for _ in sim:
            pass
    print("SWMM simulation completed.")


def main():
    BASE_INP.parent.mkdir(parents=True, exist_ok=True)
    data = load_rainfall()
    print(f"Loaded rainfall nowcast: {len(data['rainfall_forecast'])} forecast points")
    update_swmm_rainfall(data)
    run_swmm()
    print("\nOUTPUT:")
    print(OUTPUT_FILE)
    print(REPORT_FILE)


if __name__ == "__main__":
    main()