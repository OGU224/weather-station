"""Private Core2 config template.

Copy this file to /flash/device_config.py on the Core2 and fill in real values.
Do not commit real WiFi passwords or local IP addresses.
"""

ACTIVE_PROFILE = "university"
DEVICE_ID = "m5stack-env3"  # Use a unique value per Core2, for example "m5stack-co2".
SENSOR_MODE = "env3"  # "env3" or "co2"

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
