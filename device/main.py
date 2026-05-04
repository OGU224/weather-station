"""M5Stack Core2 weather station with a small assistant page.

Buttons:
  A: switch between sensor page and assistant page
  B: on assistant page, ask the cloud assistant
  C: on assistant page, speak the last answer if WAV playback is supported
"""

from m5stack import *
from m5ui import *
from uiflow import *
import time
import unit
import ujson
import urequests

try:
    import wifiCfg
except Exception:
    wifiCfg = None

# WiFi/API profiles for Flow/M5Stack uploads.
# Change ACTIVE_PROFILE only when you move between hotspot, university, or ngrok.
WIFI_PROFILES = {
    "hotspot": {
        "ssid": "YOUR_HOTSPOT_NAME",
        "password": "YOUR_HOTSPOT_PASSWORD",
        "api": "http://YOUR_LAPTOP_HOTSPOT_IP:5000",
    },
    "university": {
        "ssid": "iot-unil",
        "password": "CHANGE_ME",
        "api": "http://CHANGE_ME_LAPTOP_IP:5000",
    },
    "ngrok": {
        "ssid": "YOUR_WIFI_NAME",
        "password": "YOUR_WIFI_PASSWORD",
        "api": "https://YOUR_NGROK_URL.ngrok-free.app",
    },
}

ACTIVE_PROFILE = "hotspot"
ACTIVE_WIFI = WIFI_PROFILES[ACTIVE_PROFILE]

WIFI_SSID = ACTIVE_WIFI["ssid"]
WIFI_PASSWORD = ACTIVE_WIFI["password"]
API_BASE_URL = ACTIVE_WIFI["api"]
DEVICE_ID = "m5stack-01"
SEND_INTERVAL_SECONDS = 60
SPEAKER_VOLUME = 12

API_BASE = API_BASE_URL.rstrip("/")
SENSOR_URL = API_BASE + "/api/sensors/reading"
ASK_URL = API_BASE + "/api/voice/ask"
DEVICE_SUMMARY_URL = API_BASE + "/api/voice/device-summary"
TTS_URL = API_BASE + "/api/voice/tts"
DEVICE_TTS_URL = API_BASE + "/api/voice/device-tts"

PAGE_SENSOR = 0
PAGE_ASSISTANT = 1

current_page = PAGE_SENSOR
pending_action = None
last_answer = "Press B to ask."
last_send_ms = 0
latest_temp = 0.0
latest_hum = 0.0
latest_motion = False
wifi_connected = False


setScreenColor(0x222222)
lcd.clear()
lcd.font(lcd.FONT_Default)

title = M5TextBox(10, 10, "Weather Station", lcd.FONT_Default, 0xFFFFFF)
line1 = M5TextBox(10, 42, "", lcd.FONT_Default, 0xFFFFFF)
line2 = M5TextBox(10, 72, "", lcd.FONT_Default, 0xFFFFFF)
line3 = M5TextBox(10, 102, "", lcd.FONT_Default, 0xFFFFFF)
line4 = M5TextBox(10, 132, "", lcd.FONT_Default, 0xFFFFFF)
line5 = M5TextBox(10, 162, "", lcd.FONT_Default, 0xFFFFFF)
footer = M5TextBox(10, 214, "A: page  B: ask  C: speak", lcd.FONT_Default, 0xAAAAAA)


def set_lines(a="", b="", c="", d="", e=""):
    line1.setText(str(a))
    line2.setText(str(b))
    line3.setText(str(c))
    line4.setText(str(d))
    line5.setText(str(e))


def short_lines(text, max_chars=30, max_lines=5):
    words = str(text).replace("\n", " ").split(" ")
    lines = []
    current = ""
    for word in words:
        if not word:
            continue
        candidate = word if not current else current + " " + word
        if len(candidate) <= max_chars:
            current = candidate
        else:
            lines.append(current)
            current = word
        if len(lines) >= max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    while len(lines) < max_lines:
        lines.append("")
    return lines[:max_lines]


def url_encode(text):
    encoded = ""
    safe = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.~"
    for char in str(text):
        if char in safe:
            encoded += char
        elif char == " ":
            encoded += "%20"
        elif char == ".":
            encoded += "."
        elif char == ",":
            encoded += "%2C"
        elif char == "%":
            encoded += "%25"
        else:
            encoded += "%20"
    return encoded


def render_sensor_page():
    title.setText("Weather Station")
    wifi_text = "connected" if wifi_connected else "not connected"
    set_lines(
        "WiFi: " + wifi_text,
        "Temp: " + str(latest_temp) + " C",
        "Hum: " + str(latest_hum) + " %",
        "Motion: " + ("yes" if latest_motion else "no"),
        "Sending every " + str(SEND_INTERVAL_SECONDS) + "s",
    )
    footer.setText("A: assistant")


def render_assistant_page():
    title.setText("Assistant")
    lines = short_lines(last_answer)
    set_lines(lines[0], lines[1], lines[2], lines[3], lines[4])
    footer.setText("A: data  B: ask  C: speak")


def render_page():
    if current_page == PAGE_ASSISTANT:
        render_assistant_page()
    else:
        render_sensor_page()


def connect_wifi():
    global wifi_connected
    if not WIFI_SSID or not WIFI_PASSWORD:
        wifi_connected = False
        set_lines("WiFi config missing", "Upload device_config.py")
        return False

    if wifiCfg is None:
        wifi_connected = False
        set_lines("wifiCfg unavailable")
        return False

    set_lines("Connecting WiFi...")
    try:
        wifiCfg.doConnect(WIFI_SSID, WIFI_PASSWORD)
        for _ in range(20):
            if wifiCfg.wlan_sta.isconnected():
                wifi_connected = True
                render_page()
                return True
            time.sleep(1)
    except Exception:
        pass

    wifi_connected = False
    render_page()
    return False


def init_env3():
    try:
        return unit.get(unit.ENV3, unit.PORTA)
    except Exception:
        return None


def init_pir():
    try:
        return unit.get(unit.PIR, unit.PORTB)
    except Exception:
        return None


def read_sensors(env3_sensor, pir_sensor):
    temp = 0.0
    hum = 0.0
    motion = False

    if env3_sensor:
        temp = round(float(env3_sensor.temperature), 1)
        hum = round(float(env3_sensor.humidity), 1)

    if pir_sensor:
        motion = True if pir_sensor.state == 1 else False

    return temp, hum, motion


def send_data_to_api(temp, hum, motion):
    payload = {
        "device_id": DEVICE_ID,
        "temperature_c": temp,
        "humidity_percent": hum,
        "motion_detected": motion,
        "co2_ppm": 400,
        "tvoc_ppb": 0,
    }

    try:
        response = urequests.post(
            SENSOR_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        status_code = response.status_code
        response.close()
        return status_code >= 200 and status_code < 300
    except Exception:
        return False


def ask_cloud_assistant():
    global last_answer
    try:
        last_answer = "Asking cloud..."
        render_assistant_page()
        url = DEVICE_SUMMARY_URL + "?device_id=" + DEVICE_ID + "&hours=24"
        response = urequests.get(url)
        data = response.json()
        response.close()
        last_answer = data.get("answer", "No answer returned.")
    except Exception:
        last_answer = "Assistant request failed."
    render_assistant_page()


def play_last_answer():
    global last_answer
    if not last_answer or last_answer == "Press B to ask.":
        last_answer = "Ask a question first."
        render_assistant_page()
        return

    # Keep Core2 speech short. Long Gemini WAV files are too large for RAM.
    speech_text = last_answer
    if len(speech_text) > 55:
        speech_text = speech_text[:52] + "..."

    try:
        set_lines("TTS: requesting...", "", "", "", "")
        url = DEVICE_TTS_URL + "?text=" + url_encode(speech_text)
        response = urequests.get(url)
        if response.status_code < 200 or response.status_code >= 300:
            response.close()
            last_answer = "TTS HTTP failed."
            render_assistant_page()
            return
    except Exception:
        last_answer = "TTS request failed."
        render_assistant_page()
        return

    try:
        set_lines("TTS: saving WAV...", "", "", "", "")
        audio_path = "/flash/assistant.wav"
        with open(audio_path, "wb") as audio_file:
            audio_file.write(response.content)
        response.close()
    except Exception:
        try:
            response.close()
        except Exception:
            pass
        last_answer = "TTS save failed."
        render_assistant_page()
        return

    try:
        set_lines("TTS: playing...", "", "", "", "")
        speaker.setVolume(SPEAKER_VOLUME)
    except Exception:
        pass

    try:
        speaker.set_vol(SPEAKER_VOLUME)
    except Exception:
        pass

    try:
        speaker.setVolume(100)
    except Exception:
        pass

    try:
        speaker.playWAV(audio_path)
        render_assistant_page()
        return
    except Exception:
        try:
            speaker.playWAV(audio_path, volume=SPEAKER_VOLUME)
            render_assistant_page()
            return
        except Exception:
            try:
                speaker.playWAV(audio_path, volume=100)
                render_assistant_page()
                return
            except Exception:
                pass

    try:
        speaker.setVolume(SPEAKER_VOLUME)
        speaker.playWAV(audio_path)
        speaker.playWAV(audio_path)
        render_assistant_page()
        return
    except Exception:
        try:
            speaker.setVolume(100)
            speaker.playWAV(audio_path)
            speaker.playWAV(audio_path)
            render_assistant_page()
            return
        except Exception:
            try:
                speaker.tone(880, 150)
            except Exception:
                pass
            last_answer = "WAV playback unsupported."
            render_assistant_page()


def on_button_a():
    global current_page
    current_page = PAGE_ASSISTANT if current_page == PAGE_SENSOR else PAGE_SENSOR
    render_page()


def on_button_b():
    global pending_action
    if current_page == PAGE_ASSISTANT:
        pending_action = "ask"


def on_button_c():
    global pending_action
    if current_page == PAGE_ASSISTANT:
        pending_action = "speak"


def register_buttons():
    try:
        btnA.wasPressed(on_button_a)
        btnB.wasPressed(on_button_b)
        btnC.wasPressed(on_button_c)
    except Exception:
        pass


def main_loop():
    global latest_temp, latest_hum, latest_motion, last_send_ms, pending_action

    render_page()
    connect_wifi()
    env3_sensor = init_env3()
    pir_sensor = init_pir()
    register_buttons()

    while True:
        latest_temp, latest_hum, latest_motion = read_sensors(env3_sensor, pir_sensor)

        now_ms = time.ticks_ms()
        if time.ticks_diff(now_ms, last_send_ms) >= SEND_INTERVAL_SECONDS * 1000:
            ok = send_data_to_api(latest_temp, latest_hum, latest_motion)
            last_send_ms = now_ms
            if current_page == PAGE_SENSOR:
                line5.setText("Sent to BQ" if ok else "Send failed")

        if pending_action == "ask":
            pending_action = None
            ask_cloud_assistant()
        elif pending_action == "speak":
            pending_action = None
            play_last_answer()

        if current_page == PAGE_SENSOR:
            render_sensor_page()

        time.sleep(0.5)


main_loop()
