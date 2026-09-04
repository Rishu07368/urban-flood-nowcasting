# Urban Flood Nowcasting Prototype

## Problem statement
This prototype addresses the Smart India Hackathon problem statement on urban flood nowcasting. It combines simulated rainfall and drainage sensor data with an actual EPA SWMM 5 model via PySWMM to generate a GIS-based nowcast for flood risk over the next 0–3 hours.

## Architecture
The application follows a layered design:

- Real-time data layer: simulated rainfall and water-level sensors
- Data ingestion and validation: common JSON payloads from the sensor abstraction
- SWMM model: EPA SWMM 5 engine executed via PySWMM
- Hydrologic and hydraulic prediction: output extraction from the SWMM simulation
- Flood risk engine: explainable scoring from rainfall, water depth, drainage stress, and model–sensor deviation
- Spatial risk mapping: GeoJSON polygon-based urban flood zones
- Frontend: interactive GIS map with time slider and risk legend

## Technologies
- Python 3.12
- PySWMM 2.1.0
- swmm-toolkit 0.16.2
- FastAPI
- Leaflet + OpenStreetMap tiles
- GeoJSON for spatial layers

## SWMM role
The project uses the existing SWMM model located at `swmm/urban_flood.inp`. The model includes rainfall gages, subcatchments, junctions, outfalls, conduits, and time-series rainfall input. The rainfall nowcast is injected into the SWMM input file and executed through PySWMM to generate the hydrologic and hydraulic result files.

## Sensor simulation
The current prototype uses software-based sensor simulation. It is explicitly designed to be replaced later by real IoT sensors or external APIs without changing the rest of the application. The abstraction is represented in the backend sensor layer using a `SensorSource` pattern.

Important: sensor values in this prototype are simulated for demonstration. The design supports future replacement with real rainfall and water-level sensors.

## Flood-risk methodology
The risk engine converts SWMM outputs and simulated sensor observations into a score between 0 and 100 using a transparent weighted approach:

- water depth contribution
- rainfall intensity contribution
- conduit/flow stress contribution
- model–sensor deviation contribution
- rate-of-rise contribution

The final risk category is mapped to five levels:

- 0–20: SAFE (GREEN)
- 21–40: LOW (YELLOW)
- 41–60: MODERATE (ORANGE)
- 61–80: HIGH (RED)
- 81–100: CRITICAL (PURPLE/DARK RED)

## 0–3 hour nowcasting
The system generates risk states for the following forecast horizons:

- NOW
- +30 minutes
- +60 minutes
- +90 minutes
- +120 minutes
- +150 minutes
- +180 minutes

The frontend presents these as a slider-driven timeline so users can move from current conditions to the 3-hour forecast.

## GIS visualization
The frontend loads the generated GeoJSON risk polygons and colours each zone according to the risk category. A small map legend and summary panel help the user quickly understand the flood situation. The main product is a full-map risk view, not a generic dashboard.

## Installation
From the project root:

```bash
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Run the backend
```bash
cd C:\Users\srish\PycharmProjects\PythonProject\urban-flood-nowcasting
.\.venv\Scripts\python.exe -m uvicorn backend.api:app --host 0.0.0.0 --port 8000
```

Then open:

```text
http://localhost:8000/
```

## Run the simulation
```bash
cd C:\Users\srish\PycharmProjects\PythonProject\urban-flood-nowcasting
.\.venv\Scripts\python.exe run_simulation.py
```

This updates the SWMM rainfall time series and executes the SWMM model. The outputs are saved under the `swmm/` directory.

## Demo instructions
1. Start the backend.
2. Open the map in the browser.
3. Use the timeline to move between NOW and +3h.
4. Observe how the risk zones change colour as the event intensifies and then recedes.
5. The synthetic rainfall event used for demonstration is:
   0, 20, 40, 80, 60, 30, 5 mm/hr.

## Future real-sensor integration
The system is structured so a real `RealSensorSource` adapter can replace the simulated sensor source. The same external data contract can later be wired to IMD/CWC feeds, telemetry APIs, or IoT devices without altering the flood risk engine or GIS map.

## Limitations
- This prototype uses synthetic rainfall data and simulated sensors for demonstration.
- The SWMM model is local and deterministic rather than connected to live hydrologic feeds.
- Map tiles rely on OpenStreetMap by default, which requires external internet access for tile loading.
- This is a software prototype intended for hackathon demonstration and early design validation.

## Current data note
The rainfall data in `data/rainfall_nowcast.json` is synthetic for demonstration. It is intentionally not labelled as live IMD data and is designed to allow future upgrade to real operational weather sources.
