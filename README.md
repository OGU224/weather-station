# Cloud Weather Station

Cloud Weather Station is an indoor/outdoor IoT weather monitor built with an
M5Stack Core2, Google Cloud, BigQuery, Streamlit, OpenWeatherMap, Google Speech
APIs, Gemini, and Spotify. It collects indoor sensor readings, combines them
with outdoor weather and forecasts, and exposes the result through both a
gamified web dashboard and an on-device Core2 interface.

## Team

- Skander Ziadi: Core2 UIFlow 2 firmware, sensor collection, WiFi profile flow,
  Google STT/TTS integration on the device, assistant flow, weather/location
  integration, Spotify morning routine, deployment support, and code cleanup.
- Ugo Bieri: STT on Core2, UI on Core2, UIStreamlit dashboard interface, gamified dashboard pages, Cloud Run
  deployment work, BigQuery setup support, and project integration. (Video editor too :)

## Demo Links

- Live dashboard:
  https://weather-dashboard-387666611940.europe-west1.run.app/
- Middleware health check:
  https://weather-middleware-387666611940.europe-west1.run.app/api/health
- Demo video:
  https://www.youtube.com/watch?v=Pb6zpVn8tew

## Main Features

- Indoor temperature and humidity from the ENV III unit.
- Indoor motion detection from the PIR unit.
- Air-quality/CO2 sessions from the Unit TVOC/eCO2 sensor.
- Outdoor current weather and forecast from OpenWeatherMap.
- BigQuery storage for indoor sensor history and outdoor weather history.
- Streamlit dashboard with live status, history, assistant, and smart-home
  comfort views.
- M5Stack Core2 UI with pages for live data, forecast, assistant, trends, WiFi
  profile selection, and character selection.
- Google Speech-to-Text and Text-to-Speech for Core2 voice interaction.
- Gemini-assisted answers with deterministic fallback logic for data questions.
- Motion-triggered smart-home routine with weather advice and Spotify mood
  playback.
- WiFi profile switching on the Core2 for home/hotspot/university networks.
- Device WiFi geolocation support through Google Geolocation API, so outdoor
  weather can follow the device location when enabled.

## Architecture

```text
M5Stack Core2
  - reads ENV III, PIR, or CO2 sensor data
  - shows local UI and handles buttons/voice
  - sends readings and audio requests to middleware

Flask middleware on Cloud Run
  - stores sensor readings in BigQuery
  - reads current/history data
  - calls OpenWeatherMap
  - calls Google STT/TTS and Gemini
  - triggers Spotify playback

BigQuery
  - stores indoor sensor readings
  - stores outdoor weather snapshots

Streamlit dashboard on Cloud Run
  - reads middleware APIs
  - displays current and historical insights
  - provides a user-facing assistant interface
```

This follows the requested three-tier architecture:

- `data/`: BigQuery models and client.
- `middleware/` and `services/`: API routes, cloud service calls, and logic.
- `dashboard/` and `device/`: web UI and Core2 UI.

## Repository Structure

```text
config/                    Environment configuration and BigQuery schema
data/                      Data models and BigQuery access layer
middleware/                Flask app and API route groups
services/                  Weather, voice, geolocation, and Spotify logic
dashboard/                 Streamlit web dashboard
dashboard/pages/           Dashboard screens
device/                    Core2 firmware and setup helpers
device/ui/                 Core2 UI drawing, screens, icons, companions
collect_data.py            Optional outdoor weather history collector
CORE2_SETUP.md             Step-by-step Core2 setup notes
CODE_WALKTHROUGH.md        File-by-file explanation for presentation prep
dockerfile.middleware      Cloud Run container for middleware
dockerfile.dashboard       Cloud Run container for dashboard
requirements.txt           Python dependencies
```

## Required Configuration

Create a private `.env` file from `.env.example`.

Important variables:

```text
OWM_API_KEY                       OpenWeatherMap API key
GOOGLE_CLOUD_PROJECT              Google Cloud project id
BQ_DATASET                        BigQuery dataset name
GEMINI_API_KEY                    Gemini API key
GOOGLE_TTS_LANGUAGE               Google TTS language
GOOGLE_STT_LANGUAGE               Google STT language
GOOGLE_GEOLOCATION_ENABLED        true/false for WiFi geolocation
GOOGLE_GEOLOCATION_API_KEY        Google Geolocation API key
SPOTIFY_CLIENT_ID                 Spotify app client id
SPOTIFY_CLIENT_SECRET             Spotify app client secret
SPOTIFY_REFRESH_TOKEN             Spotify OAuth refresh token
MIDDLEWARE_URL                    Deployed middleware URL for the dashboard
```

For local development with a service-account JSON file, set
`GOOGLE_APPLICATION_CREDENTIALS` locally. On Cloud Run, do not set this variable
to a local Windows path; Cloud Run should use the service account attached to
the service.

## BigQuery Setup

Create the dataset configured by `BQ_DATASET`, then create the sensor and
weather tables using:

```text
config/bigquery_schema.sql
```

The sensor table stores:

- `device_id`
- `temperature_c`
- `humidity_pct`
- `air_quality_index` for CO2/eCO2 ppm
- `air_quality_label`
- `co2_source`
- `motion_detected`
- `timestamp`

Two Core2 devices can run at the same time with different IDs, for example:

```text
m5stack-env3   ENV III + motion
m5stack-co2    TVOC/eCO2 + motion
```

The dashboard and assistant combine recent values across devices when needed.

## Run Locally

Install dependencies:

```powershell
pip install -r requirements.txt
```

Run the middleware:

```powershell
python -m middleware.app
```

Run the dashboard:

```powershell
python -m streamlit run dashboard/app.py
```

Optionally collect outdoor weather snapshots:

```powershell
python collect_data.py
```

## Deploy The Middleware To Cloud Run

From Google Cloud Shell:

```bash
git clone https://github.com/OGU224/weather-station.git
cd weather-station
git checkout main
```

Build the image:

```bash
cp dockerfile.middleware Dockerfile
gcloud builds submit \
  --tag europe-west1-docker.pkg.dev/weather-station-494408/cloud-run-source-deploy/weather-middleware:latest .
rm Dockerfile
```

Deploy:

```bash
gcloud run deploy weather-middleware \
  --image europe-west1-docker.pkg.dev/weather-station-494408/cloud-run-source-deploy/weather-middleware:latest \
  --region europe-west1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8080
```

Set the required environment variables in Cloud Run. At minimum:

```text
OWM_API_KEY
GOOGLE_CLOUD_PROJECT
BQ_DATASET
GEMINI_API_KEY
GOOGLE_GEOLOCATION_ENABLED
GOOGLE_GEOLOCATION_API_KEY
SPOTIFY_CLIENT_ID
SPOTIFY_CLIENT_SECRET
SPOTIFY_REFRESH_TOKEN
```

Make sure the Cloud Run service account can access BigQuery, Speech-to-Text,
Text-to-Speech, and the enabled Google APIs.

Test:

```powershell
Invoke-WebRequest -UseBasicParsing "https://weather-middleware-387666611940.europe-west1.run.app/api/health"
```

## Deploy The Dashboard To Cloud Run

Build:

```bash
cp dockerfile.dashboard Dockerfile
gcloud builds submit \
  --tag europe-west1-docker.pkg.dev/weather-station-494408/cloud-run-source-deploy/weather-dashboard:latest .
rm Dockerfile
```

Deploy:

```bash
gcloud run deploy weather-dashboard \
  --image europe-west1-docker.pkg.dev/weather-station-494408/cloud-run-source-deploy/weather-dashboard:latest \
  --region europe-west1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --set-env-vars MIDDLEWARE_URL=https://weather-middleware-387666611940.europe-west1.run.app
```

If public access is not active:

```bash
gcloud beta run services add-iam-policy-binding weather-dashboard \
  --region=europe-west1 \
  --member=allUsers \
  --role=roles/run.invoker
```

## Core2 Setup

The final Core2 firmware is:

```text
device/main.py
```

Upload the files in `device/ui/` to `/flash/ui` on the Core2. Then upload a
private `/flash/device_config.py` based on:

```text
device/device_config.example.py
```

Example for the ENV III Core2:

```python
ACTIVE_PROFILE = "university"
DEVICE_ID = "m5stack-env3"
SENSOR_MODE = "env3"
```

Example for the CO2 Core2:

```python
ACTIVE_PROFILE = "university"
DEVICE_ID = "m5stack-co2"
SENSOR_MODE = "co2"
```

Each WiFi profile contains:

```python
"profile_name": {
    "ssid": "WIFI_NAME",
    "password": "WIFI_PASSWORD",
    "api": "https://weather-middleware-387666611940.europe-west1.run.app",
}
```

The Core2 WiFi page allows switching between saved profiles. The private
`device_config.py` file is ignored by Git and must not be committed.

## Core2 Buttons

```text
A              Switch page
B              Refresh / next option
B long press   Character selection
C              Main action / ask / speak
```

Core2 pages:

```text
Data -> Forecast -> Assistant -> Trend -> WiFi -> Character
```

## Stability Notes

- If the Core2 restarts, it reconnects to the selected WiFi profile and fetches
  the latest stored reading before new readings arrive.
- If the network is temporarily unavailable, the UI keeps running and retries
  calls on later refresh cycles.
- The morning routine has a cooldown, so motion does not trigger speech
  constantly.
- If ENV III and CO2 are on separate Core2 devices, BigQuery stores both using
  distinct `device_id` values and the assistant can combine recent values.

## Security Notes

Use `.env.example` and `device/device_config.example.py` as templates.

## Use of GenAI

Generative AI was used as a development assistant during the project,
especially for parts where the implementation was less familiar to us.

The main use cases were:

- the Core2 UIFlow 2 firmware in `device/main.py`, because it involved a large
  MicroPython file, hardware-specific APIs, screen rendering, button handling,
  sensors, WiFi logic, STT/TTS, and the morning routine;
- the Streamlit dashboard, where GenAI helped speed up the UI structure,
  visual styling, charts, and gamified interface ideas;
- code cleanup, debugging support, and documentation wording.

Even though GenAI helped in several parts of the repository, the code was not
left as a black box. Each feature was tested on the real Core2 devices or in
the deployed dashboard/middleware, adjusted to match the project requirements,
and reviewed so that the team can explain how the implementation works.

Also GenAI was used to format the readme file to make it more presentable.

