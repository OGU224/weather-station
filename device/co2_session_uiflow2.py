"""Small UIFlow2 CO2 collection script.

Use this only for short CO2 sessions with the Unit TVOC/eCO2 on PORTA.
This version avoids UI widgets to prevent Core2 firmware crashes.
Watch the WebTerminal for CO2 values and HTTP status.
"""

import time
import ujson

try:
    import requests
except Exception:
    import urequests as requests

from hardware import I2C, Pin

try:
    import device_config
except Exception:
    device_config = None

DEVICE_ID = "m5stack-01"
SEND_SECONDS = 15
ACTIVE_PROFILE = "university"

if device_config:
    ACTIVE_PROFILE = getattr(device_config, "ACTIVE_PROFILE", ACTIVE_PROFILE)
    WIFI_PROFILES = getattr(device_config, "WIFI_PROFILES", {})
else:
    WIFI_PROFILES = {}

ACTIVE_WIFI = WIFI_PROFILES.get(ACTIVE_PROFILE, {})
WIFI_SSID = ACTIVE_WIFI.get("ssid", "")
WIFI_PASSWORD = ACTIVE_WIFI.get("password", "")
API_BASE = ACTIVE_WIFI.get("api", "").rstrip("/")
SENSOR_URL = API_BASE + "/api/sensors/reading"


def log(message):
    print("[CO2]", message)


def connect_wifi():
    import network
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        return True

    log("WiFi waiting")
    for _ in range(8):
        if wlan.isconnected():
            return True
        time.sleep(1)

    log("WiFi reconnecting to " + WIFI_SSID)
    try:
        wlan.disconnect()
        time.sleep(1)
    except Exception:
        pass

    try:
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    except Exception as exc:
        log("WiFi connect retry: " + str(exc)[:32])
        time.sleep(3)

    for _ in range(30):
        if wlan.isconnected():
            return True
        time.sleep(1)
    return wlan.isconnected()


def sgp30_write(i2c, command):
    i2c.writeto(0x58, bytearray([(command >> 8) & 0xFF, command & 0xFF]))


def sgp30_read(i2c):
    sgp30_write(i2c, 0x2008)
    time.sleep_ms(20)
    data = i2c.readfrom(0x58, 6)
    co2 = (data[0] << 8) | data[1]
    tvoc = (data[3] << 8) | data[4]
    return co2, tvoc


def send_reading(co2, tvoc):
    payload = {
        "device_id": DEVICE_ID,
        "temperature_c": None,
        "humidity_percent": None,
        "motion_detected": False,
        "co2_ppm": co2,
        "tvoc_ppb": tvoc,
        "co2_source": "sensor",
    }
    response = requests.post(
        SENSOR_URL,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=5,
    )
    status = response.status_code
    try:
        response.close()
    except Exception:
        pass
    return status


if not connect_wifi():
    log("WiFi failed")
    while True:
        time.sleep(1)

log("WiFi OK")
log("API " + API_BASE)

i2c = I2C(0, scl=Pin(33), sda=Pin(32), freq=100000)
sgp30_write(i2c, 0x2003)
time.sleep_ms(50)
log("SGP30 init sent")

last_send = 0
last_co2 = "--"
last_tvoc = "--"
last_status = "warming up"

while True:
    try:
        co2, tvoc = sgp30_read(i2c)
        last_co2 = co2
        last_tvoc = tvoc
        now = time.ticks_ms()
        if time.ticks_diff(now, last_send) >= SEND_SECONDS * 1000:
            status = send_reading(co2, tvoc)
            last_status = "sent HTTP " + str(status)
            last_send = now
            log("CO2 " + str(co2) + " ppm, TVOC " + str(tvoc) + " ppb, " + last_status)
    except Exception as exc:
        last_status = "error " + str(exc)[:24]
        log(last_status)
    time.sleep(1)
