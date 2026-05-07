# Weather Station - Cloud Analytics

Indoor/outdoor weather station using an M5Stack Core2, Flask middleware,
Google BigQuery, OpenWeatherMap, Gemini, and a Streamlit dashboard.

## What It Does

- Core2 collects indoor readings and sends them to Flask.
- Flask validates readings and stores them in BigQuery.
- Outdoor weather is fetched from OpenWeatherMap and can be stored in BigQuery.
- Streamlit shows real-time conditions, history, insights, and an ask-data page.
- Gemini answers dashboard/Core2 questions and generates Core2 speech audio.

## Architecture

```text
M5Stack Core2  ->  Flask middleware  ->  BigQuery
                         |
                         +-> OpenWeatherMap
                         +-> Gemini API
                         |
                    Streamlit dashboard
```

## Main Commands

Install dependencies:

```powershell
pip install -r requirements.txt
```

Run the Flask middleware:

```powershell
python -m middleware.app
```

Run the dashboard:

```powershell
python -m streamlit run dashboard/app.py
```

Collect outdoor weather periodically:

```powershell
python collect_data.py
```

## Configuration

Copy `.env.example` to `.env` and fill in:

```text
OWM_API_KEY
GOOGLE_CLOUD_PROJECT
GOOGLE_APPLICATION_CREDENTIALS
BQ_DATASET
GEMINI_API_KEY
```

Do not commit `.env`.

For Core2 WiFi/API values, use `device/main_local.py`. It is ignored by git.
Keep real WiFi passwords out of `device/main.py`.

## Core2 Sensor Modes

The Core2 script has a `SENSOR_MODE` setting:

```python
SENSOR_MODE = "env3"
```

Use:

- `"env3"` when the ENV III sensor is connected on Port A.
- `"co2"` when the CO2 sensor is connected on Port A.

Because both units use Port A, temperature/humidity and CO2 are collected in
separate sessions. The dashboard/assistant combines them by recent time window,
not by assuming they came from the same row.

## Project Structure

```text
config/       Environment and BigQuery schema
data/         Dataclasses and BigQuery client
middleware/   Flask API routes
services/     Weather and assistant services
dashboard/    Streamlit dashboard
device/       Core2 script
```
