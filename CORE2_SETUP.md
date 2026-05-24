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

## 3. Prepare The UIFlow 2 File

The public firmware is:

```text
device/main.py
```

It contains placeholder WiFi/API values. For real testing, keep a private local
copy such as:

```text
device/main_uiflow2_local.py
```

Local files matching `device/*_local*.py` are ignored by Git.

## 4. Select The Profile

In the local copy, update:

```python
ACTIVE_PROFILE = "hotspot"
```

or:

```python
ACTIVE_PROFILE = "university"
```

Then set the matching SSID, password, and API URL in `WIFI_PROFILES`.

## 5. Upload With UIFlow 2

1. Open UIFlow 2.
2. Select Core2.
3. Connect through USB.
4. Paste the local firmware copy as `main.py`.
5. Run it on the device.

## 6. Sensor Mode

Use ENV III mode for temperature and humidity:

```python
SENSOR_MODE = "env3"
```

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
Data -> Forecast -> Assistant -> Data
```

## 8. Demo Checklist

- Laptop service is running.
- Dashboard is running.
- Core2 is on the same network as the laptop.
- The API URL in the Core2 local file uses the laptop IP.
- ENV III or CO2 sensor is connected to Port A.
- PIR motion sensor is connected.
- Spotify app is open if testing mood music.
