import requests
from datetime import datetime, timezone

def test_flask_api():
    url = "http://127.0.0.1:5000/api/sensors/reading"
    
    payload = {
        "device_id": "m5stack-01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature_c": 24.1,
        "humidity_percent": 50.2,
        "co2_ppm": 450,
        "tvoc_ppb": 120,
        "motion_detected": True
    }
    
    print(f"Sending POST request to {url}...")
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to the server. Is app.py running?")

if __name__ == "__main__":
    test_flask_api()
