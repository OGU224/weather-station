"""
Copy this file to device_config.py before uploading to the Core2.

Do not commit device_config.py. It contains your home WiFi and tunnel URL.
"""

WIFI_SSID = "YOUR_HOME_WIFI"
WIFI_PASSWORD = "YOUR_HOME_WIFI_PASSWORD"

# Use your ngrok/Cloud Run URL with no trailing slash.
# Example: "https://abcd-1234.ngrok-free.app"
API_BASE_URL = "https://PASTE-YOUR-NGROK-URL-HERE"

DEVICE_ID = "m5stack-01"
SEND_INTERVAL_SECONDS = 60
