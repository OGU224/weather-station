# Core2 Setup

This project uses UIFlow 2 for the final Core2 firmware.

## 1. Start The Local Service

On the laptop:

```powershell
python -m middleware.app
```

The Core2 and laptop must be on the same reachable network.

## 2. Find The Laptop IP

Use:

```powershell
ipconfig
```

Use the IPv4 address from the active WiFi network in the Core2 API URL:

```text
http://YOUR_COMPUTER_IP:5000
```

## 3. Prepare The Core2 WiFi Config

The public firmware is clean and does not need real WiFi passwords. Put local
credentials in a private config file on the Core2 instead.

Copy:

```text
device/device_config.example.py
```

to the Core2 as:

```text
/flash/device_config.py
```

Then edit the values:

```python
WIFI_PROFILES = {
    "hotspot": {
        "ssid": "YOUR_HOTSPOT_SSID",
        "password": "YOUR_HOTSPOT_PASSWORD",
        "api": "http://YOUR_COMPUTER_IP:5000",
    },
    "university": {
        "ssid": "iot-unil",
        "password": "YOUR_UNIVERSITY_WIFI_PASSWORD",
        "api": "http://YOUR_COMPUTER_IP:5000",
    },
}
```

`device/device_config.py` is ignored by Git. Do not commit real passwords.

The Core2 WiFi page lets you choose between the configured profiles at boot.

## 5. Upload With UIFlow 2

1. Open UIFlow 2.
2. Select Core2.
3. Connect through USB.
4. Upload the `device/ui` folder contents to `/flash/ui`.
5. Upload `/flash/device_config.py` with your real WiFi/API values.
6. Paste `device/main.py` or your private local copy as `main.py`.
7. Run it on the device.

If the UIFlow 2 file manager does not let you create `/flash/ui`, upload the UI
files directly into `/flash`. The firmware checks both `/flash/ui` and `/flash`.

## 6. Sensor Mode

Use ENV III mode for temperature and humidity:

```python
SENSOR_MODE = "env3"
```

For a short CO2-only validation run, you can also run:

```text
device/co2_session_uiflow2.py
```

This diagnostic script prints CO2/TVOC values in the UIFlow WebTerminal and
sends them to the middleware every 15 seconds. Use the main firmware for demos.

Use CO2 mode when the CO2 unit is connected on Port A:

```python
SENSOR_MODE = "co2"
```

Because ENV III and CO2 both use Port A, collect them in separate sessions.

## 7. Buttons

```text
A = switch page
B = refresh / next option
C = action / ask / speak
```

Pages:

```text
Data -> Forecast -> Assistant -> Trend -> Data
```

## 8. Demo Checklist

- Laptop service is running.
- Dashboard is running.
- Core2 is on the same network as the laptop.
- The API URL in the Core2 local file uses the laptop IP.
- ENV III or CO2 sensor is connected to Port A.
- PIR motion sensor is connected.
- Spotify app is open if testing mood music.
