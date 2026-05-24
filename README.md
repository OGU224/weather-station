# Weather Station

Smart indoor/outdoor weather station with a Streamlit dashboard, M5Stack Core2
interface, voice assistant, weather recommendations, and Spotify mood playback.

## Final Features

- Indoor temperature, humidity, motion, and optional CO2 collection.
- Outdoor weather and forecast collection.
- Dashboard with Home Base, Live Map, History Vault, and AI Console pages.
- Voice assistant with speech input and spoken answers.
- Morning routine: motion triggers a short weather briefing, outfit advice, and
  mood music.
- Historical comfort and air-quality analysis.

## Architecture

```text
M5Stack Core2
    -> local Python service
        -> cloud storage
        -> weather provider
        -> assistant and voice services
        -> Spotify playback

Streamlit dashboard
    -> local Python service
```

## Run The Project

Install dependencies:

```powershell
pip install -r requirements.txt
```

Run the local service:

```powershell
python -m middleware.app
```

Run the dashboard:

```powershell
python -m streamlit run dashboard/app.py
```

Collect outdoor weather in the background:

```powershell
python collect_data.py
```

## Core2 Firmware

The final Core2 firmware is:

```text
device/main.py
```

For UIFlow 2, copy that file into the UIFlow editor as `main.py`.

The public file contains placeholder WiFi/API values. Keep your real local
values in an ignored local copy such as:

```text
device/main_uiflow2_local.py
```

## Sensor Modes

The Core2 uses this setting:

```python
SENSOR_MODE = "env3"
```

Use:

- `"env3"` for ENV III temperature and humidity readings.
- `"co2"` when collecting CO2 readings.

Because ENV III and CO2 both use Port A, they are collected in separate
sessions. The dashboard and assistant combine recent readings by time window.

## Files To Know For The Presentation

```text
device/main.py                  Core2 UIFlow 2 firmware
middleware/app.py               Local service entry point
middleware/routes/              Service endpoints
services/weather_service.py     Outdoor weather
services/voice_service.py       Assistant, speech input, speech output
services/spotify_service.py     Mood music playback
data/bigquery_client.py         Cloud data access
dashboard/app.py                Dashboard shell and navigation
dashboard/pages/                Dashboard screens
collect_data.py                 Outdoor weather collector
```

## Private Files

Do not commit:

- `.env`
- `device/*_local*.py`
- service-account JSON files
- generated `artifacts/`
