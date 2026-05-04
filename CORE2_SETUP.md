# Core2 To BigQuery Setup

Use this checklist when setting up the M5Stack Core2 at home.

## 1. Verify BigQuery From Your Laptop

From the project root:

```powershell
cd D:\Courses\CloudAnalytics\CloudProject\weather-station-main\weather-station-main
python test_bq.py
```

Expected result: the script inserts a test row and reads it back.

If it fails, fix Google credentials before using the Core2. The Core2 sends data to Flask, but Flask is what writes to BigQuery.

## 2. Start The Flask Middleware

```powershell
python -m middleware.app
```

Then check:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5000/api/health
```

Expected result:

```json
{"status":"ok","message":"Weather Station API is running!"}
```

## 3. Expose Flask To The Core2

The Core2 cannot call `127.0.0.1` on your laptop. Choose one of these options.

### Option A: Home WiFi / Same Network

Use this first at home. Find your laptop IP:

```powershell
ipconfig
```

Look for the IPv4 address, for example:

```text
192.168.1.42
```

Your Core2 API base URL will be:

```text
http://192.168.1.42:5000
```

Test it from your phone while connected to the same WiFi:

```text
http://192.168.1.42:5000/api/health
```

If your phone can open it, the Core2 should be able to call it too.

### Option B: Tunnel Or Deployment

Use this for demos, school WiFi, or when the Core2 is not on the same network as your laptop. A tunnel such as ngrok works:

```powershell
ngrok http 5000
```

Copy the HTTPS forwarding URL, for example:

```text
https://abcd-1234.ngrok-free.app
```

## 4. Configure The Core2 Script

The current `device/main.py` keeps WiFi and Flask profiles directly in the
file because this is the most reliable path when pasting/running code through
Flow/M5Stack:

```python
ACTIVE_PROFILE = "hotspot"
```

Available profiles are:

```python
"hotspot"
"university"
"ngrok"
```

Before uploading to Core2, update the selected profile values at the top of
`device/main.py`. If your hotspot/laptop IP changes, update the `"api"` value
for that profile before uploading.

Do not commit real WiFi passwords. For day-to-day work, copy:

```text
device/main.py
```

to:

```text
device/main_local.py
```

Put your real WiFi passwords and current laptop/ngrok URL in
`device/main_local.py`, then paste/upload that local file to Flow/M5Stack.
`device/main_local.py` is ignored by git.

For the in-class presentation, set:

```python
ACTIVE_PROFILE = "university"
```

and fill the university profile:

```python
"university": {
    "ssid": "iot-unil",
    "password": "YOUR_IOT_UNIL_PASSWORD",
    "api": "http://YOUR_LAPTOP_IP:5000",
}
```

This keeps the required WiFi switching capability visible in the code while
keeping credentials out of Git.

## 4b. Optional Separate Config File

Copy:

```text
device/device_config.example.py
```

to:

```text
device/device_config.py
```

Fill in:

```python
WIFI_SSID = "your_home_wifi"
WIFI_PASSWORD = "your_home_wifi_password"
API_BASE_URL = "http://your-laptop-ip:5000"
DEVICE_ID = "m5stack-01"
SEND_INTERVAL_SECONDS = 60
```

For ngrok or Cloud Run, replace `API_BASE_URL` with the HTTPS URL.

Do not commit `device/device_config.py`.

## 5. Upload Files To The Core2

If using the direct-profile workflow, upload/paste:

```text
device/main_local.py
```

as `main.py` in Flow/M5Stack.

If using the optional separate config workflow, upload both files:

```text
device/main.py
device/device_config.py
```

Run `main.py` on the Core2.

## 6. Confirm Data Arrives

The Core2 should show:

```text
WiFi: connected
Status: sent to BigQuery
```

Then check the latest row:

```powershell
python -c "from data.bigquery_client import BigQueryClient; print(BigQueryClient().get_latest_sensor_reading('m5stack-01'))"
```

Or open the dashboard:

```powershell
streamlit run dashboard/app.py
```

## 7. Use The Core2 Assistant Page

The Core2 now has two pages:

- Page 1: WiFi, temperature, humidity, motion, BigQuery sending status
- Page 2: Cloud assistant

Buttons:

```text
A = switch page
B = ask the cloud assistant
C = speak the last assistant answer
```

The assistant uses `/api/voice/ask` for the answer and `/api/voice/tts`
for Gemini speech audio. Keep Flask running and make sure `GEMINI_API_KEY`
is set in `.env`.

## Common Problems

`WiFi: missing config`

You did not upload `device_config.py` or the WiFi fields are empty.

`WiFi: failed`

The SSID/password is wrong, or the WiFi network is not compatible with the Core2.

`Status: send failed`

Flask is not running, ngrok is not running, or `API_BASE_URL` is wrong.

No new BigQuery row

Check the Flask console logs and run `python test_bq.py` to confirm laptop-to-BigQuery credentials still work.
