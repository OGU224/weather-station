# Code Walkthrough

This file is the revision guide for understanding the project end to end.

## 1. Big Picture

The project has four main parts:

```text
Core2 device
  -> sends sensor readings and voice/audio requests
  -> Flask middleware
      -> BigQuery for storage/history
      -> OpenWeatherMap for outdoor weather
      -> Gemini/Google Speech for assistant, STT, and TTS
      -> Spotify Web API for mood playback
  -> Streamlit dashboard for the user interface
```

The Core2 and dashboard never write directly to BigQuery. They go through the
middleware or use the same BigQuery helper classes as a fallback.

## 2. Core2 Firmware

Main file:

```text
device/main.py
```

Private runtime config on the Core2:

```text
/flash/device_config.py
```

Template committed to Git:

```text
device/device_config.example.py
```

The public `main.py` contains placeholders. Real WiFi passwords, laptop API
URLs, and `SENSOR_MODE` live in `/flash/device_config.py`.

Important settings:

```python
ACTIVE_PROFILE = "university"
SENSOR_MODE = "env3"  # or "co2"
```

### Core2 Flow

1. Load WiFi/API config.
2. Connect to the selected WiFi profile.
3. Fetch latest stored sensor reading, outdoor weather, and forecast.
4. Initialize the active sensor mode.
5. Render the Undertale-style UI.
6. Loop forever:
   - read sensors,
   - send readings every `SEND_SECONDS`,
   - refresh weather/forecast/trends,
   - handle buttons,
   - trigger the morning routine if motion is detected.

### Sensor Modes

`SENSOR_MODE = "env3"`:

- reads ENV III temperature and humidity from Port A;
- reads PIR motion;
- sends temperature, humidity, motion, and `co2_source = "not measured"`.

`SENSOR_MODE = "co2"`:

- reads Unit TVOC/eCO2 from Port A using SGP30 I2C command `0x2008`;
- sends `co2_ppm`, TVOC diagnostic data, motion, and `co2_source = "sensor"`;
- sends temperature/humidity as null because ENV III is not connected.

This split is intentional: ENV III and TVOC/eCO2 both need Port A, so the
project collects them in separate sessions.

### Core2 UI Files

```text
device/ui/components.py  low-level drawing helpers
device/ui/companion.py   pixel companion sprites and states
device/ui/icons.py       weather icons
device/ui/screens.py     page layouts
```

Pages:

```text
Data -> Forecast -> Assistant -> Trend -> Data
```

At boot, the WiFi page lets the user select a saved WiFi profile.

Buttons:

```text
A = switch page
B = refresh / next option
C = action / ask / speak
B long press = avatar selection
```

## 3. Middleware

Entry point:

```text
middleware/app.py
```

Run it with:

```powershell
python -m middleware.app
```

Registered route groups:

```text
/api/sensors
/api/weather
/api/voice
/api/music
```

### Sensor Routes

File:

```text
middleware/routes/sensor_routes.py
```

Important endpoints:

```text
POST /api/sensors/reading
GET  /api/sensors/latest
GET  /api/sensors/history?hours=24
```

The POST route receives Core2 readings and stores them as `SensorReading`.
For CO2 mode, `air_quality_index` stores the eCO2 ppm value and `co2_source`
marks whether it came from the sensor.

### Weather Routes

File:

```text
middleware/routes/weather_routes.py
```

Important endpoints:

```text
GET /api/weather/current
GET /api/weather/current?store=true
GET /api/weather/forecast?days=3
GET /api/weather/history?hours=24
```

`WeatherService` calls OpenWeatherMap. Stored outdoor readings go to BigQuery
when `store=true` or when `collect_data.py` runs.

### Voice Routes

File:

```text
middleware/routes/voice_routes.py
```

Important endpoints:

```text
POST /api/voice/ask
POST /api/voice/device-audio-question
GET  /api/voice/device-tts?text=...
POST /api/voice/device-stt
```

These routes adapt responses for the Core2: shorter text, complete sentences,
and retry logic for TTS.

### Music Routes

File:

```text
middleware/routes/music_routes.py
```

Important endpoints:

```text
GET  /api/music/spotify/auth-url
GET  /api/music/spotify/callback
GET  /api/music/spotify/devices
POST /api/music/play-mood
```

The Core2 does not stream Spotify audio itself. It asks the middleware to start
playback on a Spotify device linked to the user's account.

## 4. Services

```text
services/weather_service.py  OpenWeatherMap calls
services/voice_service.py    Gemini, Google STT/TTS, deterministic answers
services/spotify_service.py  Spotify OAuth and playback
```

### Voice Service Logic

`services/voice_service.py` has three answer layers:

1. Deterministic answers for common data questions.
2. Gemini answers using the current/historical context.
3. Fallback answers if Gemini is unavailable.

Important functions:

```text
build_context()          loads latest/history/weather/forecast data
detect_intent()          classifies the question
deterministic_answer()   answers known cases reliably
_historical_answer()     handles "yesterday", "2 days ago", thresholds
answer_question()        main public function used by routes
```

This is why questions like "Did humidity exceed 50% yesterday?" can use stored
BigQuery data instead of only generic LLM text.

## 5. Data Layer

```text
data/models.py
data/bigquery_client.py
```

`models.py` defines the dataclasses used by the rest of the app.

`BigQueryClient` handles:

```text
insert_sensor_reading()
get_latest_sensor_reading()
get_sensor_history()
insert_weather_data()
get_weather_history()
```

Sensor and weather history are stored in separate tables. The dashboard and
assistant combine them at read time.

## 6. Dashboard

Entry point:

```text
dashboard/app.py
```

Pages:

```text
dashboard/pages/smart_home.py  gamified home command center
dashboard/pages/current.py     live indoor/outdoor station
dashboard/pages/history.py     historical charts and analysis
dashboard/pages/ask.py         assistant UI
dashboard/pages/game.py        companion training mini-game
```

Reusable charts:

```text
dashboard/components/charts.py
```

The dashboard is user-facing. It should avoid exposing backend details such as
BigQuery or Flask unless debugging is needed.

## 7. Scripts

```text
collect_data.py
```

Stores outdoor weather periodically by calling the middleware/weather service.

```text
device/co2_session_uiflow2.py
```

Small diagnostic script for validating the CO2 sensor without the full UI. Use
it for testing only; the demo should use `device/main.py`.

## 8. What To Explain During Presentation

- The Core2 has two sensor modes because ENV III and TVOC/eCO2 share Port A.
- CO2 sessions store air quality rows with null temperature/humidity.
- The dashboard and assistant use time windows to combine recent readings.
- Motion does not speak constantly; the morning routine has a cooldown.
- STT/TTS are handled through Google APIs via the middleware.
- Gemini is used for realistic answer variation, but common data questions have
  deterministic logic for reliability.
- Spotify playback is triggered through the Spotify Web API on an external
  playback device.

## 9. Safe Cleanup Rules

- Do not commit `.env`, real WiFi credentials, or service-account JSON files.
- Do not edit `device/main.py` for local WiFi changes; edit
  `/flash/device_config.py` instead.
- Keep `device/co2_session_uiflow2.py` as a diagnostic helper.
- Remove generated `__pycache__` folders locally if they bother you; Git already
  ignores them.
