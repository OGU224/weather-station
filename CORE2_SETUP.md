# Core2 Setup

This is the current Core2 workflow for the project.

## 1. Start Flask

On the laptop:

```powershell
python -m middleware.app
```

Check it:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5000/api/health
```

## 2. Find The Laptop IP

The Core2 cannot use `127.0.0.1`. Find the laptop IPv4 address:

```powershell
ipconfig
```

Example API base URL:

```text
http://130.223.162.160:5000
```

The Core2 and laptop must be on the same reachable network.

## 3. Use `main_local.py`

Keep the public-safe version in git:

```text
device/main.py
```

For real WiFi passwords and current laptop IP, use:

```text
device/main_local.py
```

`main_local.py` is ignored by git. Paste/upload it to FlowM5Stack as the Core2
`main.py`.

## 4. Choose The Network Profile

At the top of `main_local.py`, update:

```python
ACTIVE_PROFILE = "hotspot"
```

or:

```python
ACTIVE_PROFILE = "university"
```

Make sure the selected profile has the right SSID, password, and API URL.

## 5. Choose The Sensor Mode

Use ENV III mode for temperature and humidity:

```python
SENSOR_MODE = "env3"
```

Use CO2 mode when the CO2 unit is connected on Port A:

```python
SENSOR_MODE = "co2"
```

PIR motion can stay on Port B.

## 6. Core2 Pages

Button `A` cycles pages:

```text
Data -> Forecast -> Assistant -> Data
```

On the assistant page:

```text
B = next question
C = ask / speak answer
```

The assistant displays a longer answer but speaks a short `speech` summary to
avoid huge WAV files on the Core2.

## 7. Verify Data In BigQuery

Recent rows:

```sql
SELECT
  timestamp,
  device_id,
  temperature_c,
  humidity_pct,
  air_quality_index AS co2_ppm,
  co2_source,
  air_quality_label,
  motion_detected
FROM `weather-station-494408.weather_station.sensor_readings`
ORDER BY timestamp DESC
LIMIT 20;
```

Real CO2 rows only:

```sql
SELECT
  timestamp,
  device_id,
  air_quality_index AS co2_ppm,
  co2_source,
  air_quality_label
FROM `weather-station-494408.weather_station.sensor_readings`
WHERE co2_source = "sensor"
ORDER BY timestamp DESC
LIMIT 50;
```

## Common Problems

`WiFi failed`

SSID/password is wrong, or the network is not compatible with the Core2.

`Send failed`

Flask is not running, the laptop IP changed, or the selected profile API URL is
wrong.

`TTS HTTP 500`

Flask reached Gemini TTS but audio generation failed. Restart Flask and check
the Flask terminal for the exact error.

Outdoor weather missing

Check `OWM_API_KEY` in `.env`, restart Flask, and verify:

```powershell
Invoke-RestMethod http://127.0.0.1:5000/api/weather/current
```
