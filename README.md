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
    -> Flask middleware
        -> BigQuery storage
        -> OpenWeatherMap outdoor weather
        -> Gemini / Google Speech assistant services
        -> Spotify playback trigger

Streamlit dashboard
    -> Flask middleware and BigQuery fallback
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

The public file contains placeholder WiFi/API values. Put real WiFi profiles,
API URLs, and the active sensor mode in a private Core2 file:

```text
/flash/device_config.py
```

Use `device/device_config.example.py` as the template. Do not commit the real
`device_config.py` file.

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

For quick CO2 validation, `device/co2_session_uiflow2.py` can be run from
UIFlow 2. The final demo should use `device/main.py`.

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
CODE_WALKTHROUGH.md             File-by-file explanation for presentation prep
```

## Private Files

Do not commit:

- `.env`
- `device/*_local*.py`
- service-account JSON files
- generated `artifacts/`
