"""M5Stack Core2 weather station firmware for UIFlow 2.

Final UIFlow 2 firmware. Copy it into UIFlow 2 as main.py, then set local
WiFi/API values in your private copy.

Buttons:
  A: switch page
  B: refresh on data page, next question on assistant page
  C: ask selected question, record voice question, or speak answer
"""

import time
import ujson
import sys

try:
    import requests
except Exception:
    import urequests as requests

try:
    import network
except Exception:
    network = None

import M5
from M5 import *

try:
    from hardware import I2C, Pin
except Exception:
    I2C = None
    Pin = None

try:
    from unit import ENVUnit
except Exception:
    ENVUnit = None

for _path in ("/flash", "/flash/ui", "ui", "device/ui"):
    try:
        if _path not in sys.path:
            sys.path.append(_path)
    except Exception:
        pass

try:
    from components import init as ui_init, clear_screen
    from companion import Buddy, CHARACTERS
    from screens import (
        render as render_undertale,
        render_busy_screen,
        PAGE_DATA,
        PAGE_FORECAST,
        PAGE_ASSISTANT,
        PAGE_WIFI,
        PAGE_CHARACTER,
        PAGE_COUNT,
    )
    UNDERTALE_UI = True
except Exception:
    UNDERTALE_UI = False

# ---------------------------------------------------------------------------
# Local setup. Keep real passwords/IPs in your UIFlow copy or main_uiflow2_local.py.
# ---------------------------------------------------------------------------

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

# Change this in your local UIFlow copy when moving between networks.
ACTIVE_PROFILE = "university"
ACTIVE_WIFI = WIFI_PROFILES[ACTIVE_PROFILE]

WIFI_SSID = ACTIVE_WIFI["ssid"]
WIFI_PASSWORD = ACTIVE_WIFI["password"]
API_BASE_URL = ACTIVE_WIFI["api"]
DEVICE_ID = "m5stack-01"
SENSOR_MODE = "env3"  # "env3" or "co2" once a UIFlow 2 CO2 reader is added.

SEND_SECONDS = 60
WEATHER_SECONDS = 300
RENDER_SECONDS = 15
RECORD_SECONDS = 4
STT_LANGUAGE = "en-US"
SPEAKER_VOLUME_PERCENT = 70
SHOW_TRANSCRIPT_SECONDS = 2
MORNING_ROUTINE_ENABLED = True
MORNING_COOLDOWN_SECONDS = 900
SPOTIFY_MUSIC_ENABLED = True
LOCAL_MUSIC_FALLBACK_ENABLED = False
SPOTIFY_TIMEOUT_SECONDS = 18
MORNING_QUESTION = (
    "Generate a very short smart-home morning briefing for someone who just entered "
    "the room. Use exactly this format with short phrases, no extra words: "
    "Good morning. Weather outside: [temperature] degrees, [weather]. "
    "Wear: [short clothing/accessory advice]."
)

# If physical buttons feel reversed after rotation, swap these labels only.
BUTTON_PAGE = "A"
BUTTON_NEXT = "B"
BUTTON_ACTION = "C"

API_BASE = API_BASE_URL.rstrip("/")
SENSOR_URL = API_BASE + "/api/sensors/reading"
WEATHER_URL = API_BASE + "/api/weather/current"
FORECAST_URL = API_BASE + "/api/weather/forecast?days=3"
ASK_URL = API_BASE + "/api/voice/ask"
DEVICE_ASK_URL = API_BASE + "/api/voice/device-audio-question"
DEVICE_TTS_URL = API_BASE + "/api/voice/device-tts"
MUSIC_MOOD_URL = API_BASE + "/api/music/play-mood"


# ---------------------------------------------------------------------------
# UI constants/state
# ---------------------------------------------------------------------------

PAGE_DATA = 0
PAGE_FORECAST = 1
PAGE_ASSISTANT = 2

QUESTIONS = [
    (
        "Rain",
        "Rain this week?",
        "Will it rain in the forecast period? Use the forecast data. Answer in at most 18 words.",
    ),
    (
        "Outfit",
        "What should I wear?",
        "Give clothing advice for today using outdoor weather. Answer in at most 18 words.",
    ),
    (
        "Room",
        "Is my room healthy?",
        "Check room health using indoor temperature, humidity, and CO2 if available. Answer in at most 18 words.",
    ),
    (
        "Ventilate",
        "Open the window?",
        "Should I open the window now using indoor humidity and outdoor weather? Answer in at most 18 words.",
    ),
    (
        "Voice",
        "Press C and speak",
        "VOICE_RECORD",
    ),
]

BG = 0x08111F
HEADER = 0x00A6D6
PANEL = 0x13263A
PANEL_2 = 0x17324B
FOOTER = 0x06101D
WHITE = 0xFFFFFF
MUTED = 0x9DB1C3
BLUE = 0x38BDF8
GREEN = 0x34D399
YELLOW = 0xFBBF24
RED = 0xF87171
PURPLE = 0x5B5FEF

page = PAGE_DATA
question_index = 0
answer_ready = False
last_answer = "Select a question."
last_transcript = ""
last_error = ""

wifi_ok = False
send_ok = False
latest_temp = None
latest_hum = None
latest_motion = False
previous_motion = False
latest_co2 = None

outdoor_ok = False
outdoor_temp = "--"
outdoor_hum = "--"
outdoor_wind = "--"
outdoor_main = "loading"
outdoor_city = "Outdoor"
forecast_days = []

env3 = None


# ---------------------------------------------------------------------------
# Small compatibility helpers
# ---------------------------------------------------------------------------

def now_ms():
    return time.ticks_ms()


def elapsed_ms(start):
    return time.ticks_diff(time.ticks_ms(), start)


def ascii_text(value):
    text = str(value or "")
    replacements = [
        ("\xe9", "e"), ("\xe8", "e"), ("\xea", "e"), ("\xeb", "e"),
        ("\xe0", "a"), ("\xe2", "a"), ("\xf9", "u"), ("\xfb", "u"),
        ("\xf4", "o"), ("\xee", "i"), ("\xef", "i"), ("\xe7", "c"),
        ("\xb0", " deg "), ("\u2019", "'"), ("\u2013", "-"), ("\u2014", "-"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return "".join(char for char in text if ord(char) < 128)


def trim(value, max_chars):
    text = ascii_text(value).replace("\n", " ")
    text = " ".join(text.split())
    if len(text) > max_chars:
        return text[: max_chars - 3].rstrip(" ,.;:") + "..."
    return text


def trim_sentence(value, max_chars):
    text = trim(value, max_chars * 2)
    if len(text) <= max_chars:
        if text and text[-1] not in ".!?":
            text += "."
        return text

    cutoff = -1
    for mark in [". ", "! ", "? "]:
        pos = text.rfind(mark, 0, max_chars)
        if pos > cutoff:
            cutoff = pos + 1

    if cutoff >= 30:
        return text[:cutoff].strip()

    return text[:max_chars].rstrip(" ,.;:") + "."


def has_outfit_advice(text):
    value = str(text or "").lower()
    keywords = [
        "umbrella",
        "sunglasses",
        "sunscreen",
        "jacket",
        "coat",
        "layers",
        "layer",
        "raincoat",
        "wear",
        "bring",
    ]
    return any(word in value for word in keywords)


def local_outfit_advice():
    weather = str(outdoor_main or "").lower()
    try:
        temp = float(outdoor_temp)
    except Exception:
        temp = None

    if "rain" in weather or "drizzle" in weather or "storm" in weather:
        return "Don't forget an umbrella or a rain jacket."
    if temp is not None and temp >= 24:
        return "Wear light clothes, and bring sunglasses and sunscreen."
    if "clear" in weather or "sun" in weather:
        return "Bring sunglasses, and use sunscreen if you stay outside."
    if temp is not None and temp <= 10:
        return "Wear a warm jacket or extra layers."
    if temp is not None and temp <= 16:
        return "A light jacket or layers would be comfortable."
    return "Dress comfortably, and take a light layer just in case."


def outdoor_weather_sentence():
    if not outdoor_ok:
        return "I could not load the outdoor weather right now."

    condition = str(outdoor_main or "weather").lower()
    condition = condition.replace("clear", "clear skies")
    condition = condition.replace("clouds", "cloudy weather")
    condition = condition.replace("rain", "rain")
    temp = str(outdoor_temp)
    hum = str(outdoor_hum)
    wind = str(outdoor_wind)
    return (
        "Outside in Lausanne, it is "
        + temp
        + " degrees with "
        + condition
        + ", "
        + hum
        + " percent humidity, and wind at "
        + wind
        + " meters per second."
    )


def morning_briefing_text():
    if not outdoor_ok:
        return "Good morning. Weather outside: unavailable. Wear: take a light layer just in case."
    return (
        "Good morning. Weather outside: "
        + str(outdoor_temp)
        + " degrees, "
        + str(outdoor_main)
        + ". Wear: "
        + local_outfit_advice().replace("Don't forget ", "").replace("Wear ", "").rstrip(".")
        + "."
    )


def ai_morning_question():
    return (
        MORNING_QUESTION
        + " Current outdoor data: city Lausanne, temperature "
        + str(outdoor_temp)
        + " degrees, weather "
        + str(outdoor_main)
        + ", humidity "
        + str(outdoor_hum)
        + " percent, wind "
        + str(outdoor_wind)
        + " meters per second. Recommended advice if needed: "
        + local_outfit_advice()
    )


def valid_morning_briefing(text):
    value = str(text or "").lower()
    if len(value) < 35:
        return False
    if not ("good morning" in value or "hello" in value):
        return False
    if not ("weather outside" in value or str(outdoor_temp).lower() in value):
        return False
    return has_outfit_advice(value)


def get_ai_morning_briefing():
    try:
        response = requests.post(
            ASK_URL,
            json={"question": ai_morning_question(), "device_id": DEVICE_ID, "hours": 24},
            headers={"Content-Type": "application/json"},
            timeout=18,
        )
        data = get_json_response(response)
        answer = trim_sentence(data.get("answer", ""), 150)
        if valid_morning_briefing(answer):
            return answer
    except Exception:
        pass
    return morning_briefing_text()


def url_encode(value):
    safe = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.~"
    encoded = ""
    for char in str(value):
        if char in safe:
            encoded += char
        elif char == " ":
            encoded += "%20"
        else:
            encoded += "%20"
    return encoded


def get_json_response(response):
    body = response.text
    try:
        response.close()
    except Exception:
        pass
    return ujson.loads(body)


def button_is_down(button):
    try:
        return button.isPressed()
    except Exception:
        try:
            return button.wasPressed()
        except Exception:
            return False


last_down = {"A": False, "B": False, "C": False}


def read_button_click():
    states = {
        "A": button_is_down(BtnA),
        "B": button_is_down(BtnB),
        "C": button_is_down(BtnC),
    }
    clicked = None
    for name in ["C", "B", "A"]:
        if states[name] and not last_down[name]:
            clicked = name
            break
    for name in ["A", "B", "C"]:
        last_down[name] = states[name]
    return clicked


def fill_rect(x, y, w, h, color):
    try:
        Widgets.Rectangle(x, y, w, h, color, color)
    except Exception:
        try:
            M5.Lcd.fillRect(x, y, w, h, color)
        except Exception:
            pass


def set_label(label, text, color=None):
    label.setText(ascii_text(text))
    if color is not None:
        try:
            label.setColor(color, BG)
        except Exception:
            pass


def set_label_on(label, text, fg, bg):
    label.setText(ascii_text(text))
    try:
        label.setColor(fg, bg)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Boot/UI objects
# ---------------------------------------------------------------------------

M5.begin()
Widgets.fillScreen(BG)

header = Widgets.Label("Cloud Weather", 12, 7, 1.0, WHITE, HEADER, Widgets.FONTS.DejaVu18)
status = Widgets.Label("", 210, 10, 1.0, WHITE, HEADER, Widgets.FONTS.DejaVu12)
line1 = Widgets.Label("", 16, 45, 1.0, WHITE, BG, Widgets.FONTS.DejaVu18)
line2 = Widgets.Label("", 16, 72, 1.0, WHITE, BG, Widgets.FONTS.DejaVu18)
line3 = Widgets.Label("", 16, 101, 1.0, WHITE, BG, Widgets.FONTS.DejaVu18)
line4 = Widgets.Label("", 16, 130, 1.0, WHITE, BG, Widgets.FONTS.DejaVu18)
line5 = Widgets.Label("", 16, 159, 1.0, WHITE, BG, Widgets.FONTS.DejaVu18)
line6 = Widgets.Label("", 16, 188, 1.0, WHITE, BG, Widgets.FONTS.DejaVu12)
footer = Widgets.Label("A:page", 12, 219, 1.0, MUTED, FOOTER, Widgets.FONTS.DejaVu12)


def clear_lines():
    set_label(line1, "")
    set_label(line2, "")
    set_label(line3, "")
    set_label(line4, "")
    set_label(line5, "")
    set_label(line6, "")


def draw_base(title, color):
    Widgets.fillScreen(BG)
    fill_rect(0, 0, 320, 32, color)
    fill_rect(0, 210, 320, 30, FOOTER)
    set_label_on(header, title, WHITE, color)
    set_label_on(status, "online" if wifi_ok else "offline", WHITE, color)
    clear_lines()


def wrap_text(text, width, max_lines):
    words = trim(text, width * max_lines + 20).split(" ")
    lines = [""]
    for word in words:
        if not word:
            continue
        candidate = word if not lines[-1] else lines[-1] + " " + word
        if len(candidate) <= width:
            lines[-1] = candidate
        elif len(lines) < max_lines:
            lines.append(word)
        else:
            lines[-1] = trim(lines[-1] + " " + word, width)
            break
    while len(lines) < max_lines:
        lines.append("")
    return lines[:max_lines]


def display_value(value, suffix=""):
    if value is None:
        return "--"
    return str(value) + suffix


def current_alert():
    if last_error:
        return trim(last_error, 22), RED
    if latest_hum is not None and latest_hum < 40:
        return "Low humidity", YELLOW
    if latest_hum is not None and latest_hum > 65:
        return "Humid room", YELLOW
    if outdoor_ok and "rain" in str(outdoor_main).lower():
        return "Rain outside", BLUE
    if send_ok:
        return "All good", GREEN
    return "Waiting upload", MUTED


def render_data(full=True):
    if full:
        draw_base("Cloud Weather", HEADER)
        fill_rect(10, 42, 145, 84, PANEL)
        fill_rect(165, 42, 145, 84, PANEL)
        fill_rect(10, 136, 300, 62, PANEL_2)

    set_label(line1, "INDOOR", BLUE)
    set_label(line2, display_value(latest_temp, " C") + "   " + display_value(latest_hum, "%"), WHITE)
    if SENSOR_MODE == "co2":
        set_label(line3, "CO2 " + display_value(latest_co2, " ppm"), MUTED)
    else:
        set_label(line3, "Motion " + ("yes" if latest_motion else "no"), MUTED)
    set_label(line4, "OUTDOOR", GREEN)
    set_label(line5, str(outdoor_temp) + " C   " + str(outdoor_hum) + "%", WHITE)
    set_label(line6, trim(str(outdoor_main) + "  wind " + str(outdoor_wind) + " m/s", 36), MUTED)
    alert, color = current_alert()
    set_label_on(status, alert, WHITE, HEADER)
    set_label_on(footer, BUTTON_PAGE + ":forecast   " + BUTTON_NEXT + ":refresh", MUTED, FOOTER)


def forecast_line(index):
    if index >= len(forecast_days):
        return "--", ""
    item = forecast_days[index]
    date = str(item.get("date", ""))
    if len(date) >= 10:
        date = date[5:10]
    try:
        high = round(float(item.get("temp_max", 0)), 1)
        low = round(float(item.get("temp_min", 0)), 1)
        temps = str(high) + "/" + str(low) + " C"
    except Exception:
        temps = "--"
    return date + "  " + temps, str(item.get("weather_main", ""))


def render_forecast(full=True):
    if full:
        draw_base("Forecast", 0x2563EB)
        fill_rect(10, 45, 300, 43, PANEL)
        fill_rect(10, 101, 300, 43, PANEL)
        fill_rect(10, 157, 300, 43, PANEL)

    d0, w0 = forecast_line(0)
    d1, w1 = forecast_line(1)
    d2, w2 = forecast_line(2)
    set_label(line1, d0, BLUE)
    set_label(line2, w0, WHITE)
    set_label(line3, d1, BLUE)
    set_label(line4, w1, WHITE)
    set_label(line5, d2, BLUE)
    set_label(line6, w2, WHITE)
    set_label_on(footer, BUTTON_PAGE + ":assistant   " + BUTTON_NEXT + ":refresh", MUTED, FOOTER)


def render_assistant(full=True):
    if full:
        draw_base("Assistant", PURPLE)
        fill_rect(10, 45, 300, 153, PANEL)

    if answer_ready:
        lines = wrap_text(last_answer, 31, 5)
        set_label(line1, "Answer", GREEN)
        set_label(line2, lines[0], WHITE)
        set_label(line3, lines[1], WHITE)
        set_label(line4, lines[2], WHITE)
        set_label(line5, lines[3], WHITE)
        set_label(line6, lines[4], WHITE)
        set_label_on(
            footer,
            BUTTON_PAGE + ":data   " + BUTTON_NEXT + ":next   " + BUTTON_ACTION + ":speak",
            MUTED,
            FOOTER,
        )
        return

    q = QUESTIONS[question_index]
    if last_transcript:
        lines = wrap_text("Heard: " + last_transcript, 31, 4)
        set_label(line1, q[0], BLUE)
        set_label(line2, lines[0], WHITE)
        set_label(line3, lines[1], WHITE)
        set_label(line4, lines[2], WHITE)
        set_label(line5, lines[3], WHITE)
    else:
        set_label(line1, q[0], BLUE)
        set_label(line2, trim(q[1], 29), WHITE)
        set_label(line3, "", WHITE)
        if q[2] == "VOICE_RECORD":
            set_label(line4, "Press C, then speak", YELLOW)
        else:
            set_label(line4, "Press C to ask", MUTED)
        set_label(line5, "", WHITE)
    set_label(line6, "", WHITE)
    set_label_on(
        footer,
        BUTTON_PAGE + ":data   " + BUTTON_NEXT + ":next   " + BUTTON_ACTION + ":ask",
        MUTED,
        FOOTER,
    )


def render(full=True):
    if page == PAGE_DATA:
        render_data(full)
    elif page == PAGE_FORECAST:
        render_forecast(full)
    else:
        render_assistant(full)


# ---------------------------------------------------------------------------
# Undertale Core2 UI integration.
#
# The original labels above stay as a fallback for UIFlow, but when the
# imported UI package is available we override the render functions only.
# Sensor, STT, TTS, morning routine and Spotify logic remain the local version.
# ---------------------------------------------------------------------------

if UNDERTALE_UI:
    try:
        ui_init()
        clear_screen()
    except Exception:
        pass

    buddy = Buddy()
    wifi_profile_keys = []
    for _key in WIFI_PROFILES:
        wifi_profile_keys.append(_key)
    wifi_profile_index = 0
    wifi_status = ""

    def _ui_wifi_profiles():
        profiles = []
        for key in wifi_profile_keys:
            data = WIFI_PROFILES[key]
            profiles.append({
                "name": key,
                "ssid": data.get("ssid", ""),
                "pwd": data.get("password", ""),
            })
        return profiles

    def _ui_answer_text():
        if answer_ready:
            return last_answer
        if last_transcript:
            return "Heard: " + last_transcript
        return last_answer

    def _ui_state():
        return {
            "temp": latest_temp,
            "hum": latest_hum,
            "send_ok": send_ok,
            "o_temp": outdoor_temp,
            "o_hum": outdoor_hum,
            "o_main": outdoor_main,
            "o_icon": "",
            "o_ok": outdoor_ok,
            "fcast": forecast_days,
            "tstr": "",
            "qi": question_index,
            "ans_ok": answer_ready,
            "ans_txt": _ui_answer_text(),
            "wifi_profiles": _ui_wifi_profiles(),
            "wifi_idx": wifi_profile_index,
            "wifi_status": wifi_status,
            "char_idx": buddy.char_idx,
        }

    def render_data(full=True):
        render_undertale(PAGE_DATA, _ui_state(), buddy, full)

    def render_forecast(full=True):
        render_undertale(PAGE_FORECAST, _ui_state(), buddy, full)

    def render_assistant(full=True):
        render_undertale(PAGE_ASSISTANT, _ui_state(), buddy, full)

    def render_wifi(full=True):
        render_undertale(PAGE_WIFI, _ui_state(), buddy, full)

    def render_character(full=True):
        render_undertale(PAGE_CHARACTER, _ui_state(), buddy, full)

    def render(full=True):
        if page == PAGE_DATA:
            render_data(full)
        elif page == PAGE_FORECAST:
            render_forecast(full)
        elif page == PAGE_ASSISTANT:
            render_assistant(full)
        elif page == PAGE_WIFI:
            render_wifi(full)
        elif page == PAGE_CHARACTER:
            render_character(full)

    def apply_wifi_profile(index):
        global WIFI_SSID, WIFI_PASSWORD, API_BASE_URL, API_BASE
        global SENSOR_URL, WEATHER_URL, FORECAST_URL, ASK_URL, DEVICE_ASK_URL
        global DEVICE_TTS_URL, MUSIC_MOOD_URL, ACTIVE_PROFILE, ACTIVE_WIFI

        key = wifi_profile_keys[index]
        ACTIVE_PROFILE = key
        ACTIVE_WIFI = WIFI_PROFILES[key]
        WIFI_SSID = ACTIVE_WIFI["ssid"]
        WIFI_PASSWORD = ACTIVE_WIFI["password"]
        API_BASE_URL = ACTIVE_WIFI["api"]
        API_BASE = API_BASE_URL.rstrip("/")
        SENSOR_URL = API_BASE + "/api/sensors/reading"
        WEATHER_URL = API_BASE + "/api/weather/current"
        FORECAST_URL = API_BASE + "/api/weather/forecast?days=3"
        ASK_URL = API_BASE + "/api/voice/ask"
        DEVICE_ASK_URL = API_BASE + "/api/voice/device-audio-question"
        DEVICE_TTS_URL = API_BASE + "/api/voice/device-tts"
        MUSIC_MOOD_URL = API_BASE + "/api/music/play-mood"

    def choose_wifi_on_boot():
        global wifi_profile_index, wifi_status
        try:
            for idx, key in enumerate(wifi_profile_keys):
                if key == ACTIVE_PROFILE:
                    wifi_profile_index = idx
                    break
        except Exception:
            pass

        wifi_status = "B: choose  C: connect"
        render_wifi(True)
        start = now_ms()
        b_down = False
        c_down = False
        while elapsed_ms(start) < 8000:
            M5.update()
            try:
                current_b = button_is_down(BtnB)
                current_c = button_is_down(BtnC)
            except Exception:
                current_b = False
                current_c = False

            if current_b and not b_down:
                wifi_profile_index = (wifi_profile_index + 1) % len(wifi_profile_keys)
                wifi_status = "B: choose  C: connect"
                render_wifi(True)
                start = now_ms()
                time.sleep_ms(250)
            elif current_c and not c_down:
                break

            b_down = current_b
            c_down = current_c
            time.sleep_ms(50)
        apply_wifi_profile(wifi_profile_index)


# ---------------------------------------------------------------------------
# Connectivity and sensors
# ---------------------------------------------------------------------------

def connect_wifi():
    global wifi_ok, last_error, wifi_status
    draw_base("WiFi", HEADER)
    set_label(line1, "Connecting...", BLUE)
    set_label(line2, WIFI_SSID, WHITE)
    set_label(line3, "Resetting WiFi", MUTED)
    if UNDERTALE_UI:
        wifi_status = "Connecting to " + WIFI_SSID
        render_wifi(True)

    if network is None:
        wifi_ok = False
        last_error = "network missing"
        if UNDERTALE_UI:
            wifi_status = "Network module missing"
        render(True)
        return False

    try:
        wlan = network.WLAN(network.STA_IF)
        try:
            wlan.disconnect()
        except Exception:
            pass
        wlan.active(False)
        time.sleep(1)
        wlan.active(True)
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        for _ in range(30):
            M5.update()
            if wlan.isconnected():
                wifi_ok = True
                last_error = ""
                try:
                    if UNDERTALE_UI:
                        wifi_status = "Connected"
                        render_wifi(True)
                    set_label(line3, "Connected", GREEN)
                    time.sleep(1)
                except Exception:
                    pass
                return True
            set_label(line3, "Waiting " + str(_ + 1) + "/30", MUTED)
            if UNDERTALE_UI:
                wifi_status = "Waiting " + str(_ + 1) + "/30"
                render_wifi(False)
            time.sleep(1)
    except Exception as exc:
        last_error = "WiFi " + str(exc)[:20]

    wifi_ok = False
    if UNDERTALE_UI:
        wifi_status = "Failed: " + trim(last_error, 20)
    set_label(line3, "WiFi failed", RED)
    set_label(line4, trim(last_error, 28), RED)
    time.sleep(2)
    return False


def init_sensors():
    global env3, last_error
    if I2C is not None and Pin is not None and ENVUnit is not None:
        try:
            i2c0 = I2C(0, scl=Pin(33), sda=Pin(32), freq=100000)
            env3 = ENVUnit(i2c=i2c0, type=3)
        except Exception as exc:
            env3 = None
            last_error = "ENV " + str(exc)[:18]


def read_sensors():
    global latest_temp, latest_hum, latest_motion
    if env3 is not None:
        try:
            latest_temp = round(float(env3.read_temperature()), 1)
            latest_hum = round(float(env3.read_humidity()), 1)
        except Exception:
            pass

    latest_motion = False
    if Pin is not None:
        try:
            motion_pin = Pin(36, mode=Pin.IN)
            latest_motion = bool(motion_pin.value())
        except Exception:
            latest_motion = False


def send_sensor_reading():
    global send_ok, last_error
    payload = {
        "device_id": DEVICE_ID,
        "temperature_c": latest_temp,
        "humidity_percent": latest_hum,
        "motion_detected": latest_motion,
        "co2_source": "not measured",
    }
    if latest_co2 is not None:
        payload["co2_ppm"] = latest_co2
        payload["co2_source"] = "sensor"

    try:
        response = requests.post(
            SENSOR_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5,
        )
        send_ok = response.status_code >= 200 and response.status_code < 300
        try:
            response.close()
        except Exception:
            pass
        if not send_ok:
            last_error = "BQ HTTP " + str(response.status_code)
    except Exception as exc:
        send_ok = False
        last_error = "Send " + str(exc)[:18]


def fetch_weather():
    global outdoor_ok, outdoor_temp, outdoor_hum, outdoor_wind, outdoor_main, outdoor_city, last_error
    try:
        response = requests.get(WEATHER_URL, timeout=5)
        if response.status_code == 200:
            data = get_json_response(response)
            outdoor_temp = str(round(float(data.get("temperature_c", 0)), 1))
            outdoor_hum = str(int(float(data.get("humidity_pct", 0))))
            outdoor_wind = str(round(float(data.get("wind_speed_ms", 0)), 1))
            outdoor_main = str(data.get("weather_main") or data.get("weather_description") or "Weather")
            outdoor_city = str(data.get("city") or "Outdoor")
            outdoor_ok = True
            return
        last_error = "Weather HTTP " + str(response.status_code)
        try:
            response.close()
        except Exception:
            pass
    except Exception as exc:
        last_error = "Weather " + str(exc)[:15]
    outdoor_ok = False


def fetch_forecast():
    global forecast_days
    try:
        response = requests.get(FORECAST_URL, timeout=5)
        if response.status_code == 200:
            forecast_days = get_json_response(response)
        else:
            try:
                response.close()
            except Exception:
                pass
    except Exception:
        pass


def local_preset_answer(question):
    q = str(question or "").lower()

    if "rain in the forecast" in q:
        rainy_days = []
        for item in forecast_days:
            main = str(item.get("weather_main", ""))
            if "rain" in main.lower() or "drizzle" in main.lower() or "storm" in main.lower():
                date = str(item.get("date", ""))
                if len(date) >= 10:
                    date = date[5:10]
                rainy_days.append(date or main)
        if rainy_days:
            return "Yes. Rain is expected on " + ", ".join(rainy_days[:3]) + ". Bring an umbrella."
        if forecast_days:
            return "No rain in the available forecast. It looks mostly dry."
        return "I do not have forecast data yet."

    if "clothing advice" in q:
        if outdoor_ok:
            return local_outfit_advice()
        return "Outdoor weather is unavailable. Take a light layer just in case."

    if "room health" in q:
        if latest_hum is not None and latest_hum < 40:
            return "Room is too dry at " + str(latest_hum) + "%. Add humidity if possible."
        if latest_hum is not None and latest_hum > 65:
            return "Room is humid at " + str(latest_hum) + "%. Ventilate for a few minutes."
        if latest_temp is not None and latest_hum is not None:
            return "Room looks healthy: " + str(latest_temp) + "C and " + str(latest_hum) + "% humidity."
        return "I need indoor sensor data to judge room health."

    if "open the window" in q:
        if latest_hum is not None and latest_hum > 65:
            return "Yes, ventilate briefly. Indoor humidity is high."
        if outdoor_ok and "rain" in str(outdoor_main).lower():
            return "Better keep it closed for now. It is raining outside."
        if latest_hum is not None and latest_hum < 40:
            return "No. The room is already dry, so ventilation may make it worse."
        return "Optional. The room looks comfortable right now."

    return None


# ---------------------------------------------------------------------------
# Assistant, STT, TTS
# ---------------------------------------------------------------------------

def ask_text(question):
    global answer_ready, last_answer, last_error
    answer_ready = False
    last_answer = "Thinking..."
    render_assistant(True)
    if not UNDERTALE_UI:
        set_label(line2, "Contacting assistant...", YELLOW)
        set_label(line3, "Please wait", MUTED)
    preset = local_preset_answer(question)
    if preset:
        last_answer = trim_sentence(preset, 160)
        answer_ready = True
        last_error = ""
        render_assistant(True)
        return
    try:
        response = requests.post(
            ASK_URL,
            json={"question": question, "device_id": DEVICE_ID, "hours": 24},
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        data = get_json_response(response)
        last_answer = trim_sentence(data.get("speech") or data.get("answer", "No answer."), 210)
        answer_ready = True
        last_error = ""
    except Exception as exc:
        last_answer = "Assistant failed."
        last_error = "Ask " + str(exc)[:18]
    render_assistant(True)


def amplify_pcm(buffer, gain):
    if gain <= 1:
        return
    for index in range(0, len(buffer) - 1, 2):
        sample = buffer[index] | (buffer[index + 1] << 8)
        if sample >= 32768:
            sample -= 65536
        sample = int(sample * gain)
        if sample > 32767:
            sample = 32767
        elif sample < -32768:
            sample = -32768
        if sample < 0:
            sample += 65536
        buffer[index] = sample & 0xFF
        buffer[index + 1] = (sample >> 8) & 0xFF


def record_pcm():
    try:
        Mic.deinit()
    except Exception:
        pass
    Mic.begin()
    sample_rate = 8000
    audio = bytearray(sample_rate * 2 * RECORD_SECONDS)
    Mic.record(audio, sample_rate, False)
    time.sleep(RECORD_SECONDS + 0.2)
    try:
        Mic.end()
    except Exception:
        pass
    amplify_pcm(audio, 3)
    return audio


def ask_by_voice():
    global answer_ready, last_answer, last_transcript, last_error
    answer_ready = False
    last_transcript = ""
    last_answer = "Speak now..."
    if UNDERTALE_UI:
        render_assistant(True)
    else:
        set_label(line1, "Voice", BLUE)
        set_label(line2, "Speak now...", YELLOW)
        set_label(line3, str(RECORD_SECONDS) + " seconds", WHITE)
        set_label(line4, "", WHITE)
        set_label(line5, "", WHITE)

    try:
        audio = record_pcm()
    except Exception as exc:
        last_error = "Mic " + str(exc)[:20]
        last_answer = "Microphone failed."
        render_assistant(True)
        return

    if not any(audio):
        last_error = "Microphone silent"
        last_answer = "No audio recorded."
        render_assistant(True)
        return

    last_answer = "Transcribing..."
    if UNDERTALE_UI:
        render_assistant(True)
    else:
        set_label(line2, "Transcribing...", YELLOW)
        set_label(line3, "Cloud STT + assistant", MUTED)
    try:
        url = (
            DEVICE_ASK_URL
            + "?language_code="
            + STT_LANGUAGE
            + "&device_id="
            + DEVICE_ID
            + "&hours=24"
        )
        response = requests.post(
            url,
            data=audio,
            headers={"Content-Type": "audio/l16"},
            timeout=25,
        )
        status_code = response.status_code
        data = get_json_response(response)
        if status_code < 200 or status_code >= 300:
            last_error = "STT HTTP " + str(status_code)
            last_answer = data.get("error", "Speech not understood.")
            render_assistant(True)
            return
        last_transcript = trim(data.get("transcript", ""), 80)
        answer_ready = False
        render_assistant(True)
        time.sleep(SHOW_TRANSCRIPT_SECONDS)
        last_answer = trim_sentence(data.get("speech") or data.get("answer", "No answer."), 210)
        answer_ready = True
        last_error = ""
    except Exception as exc:
        last_error = "STT " + str(exc)[:20]
        last_answer = "Speech request failed."
    render_assistant(True)


def play_mood_music(condition=""):
    mood = str(condition or "").lower()
    if "rain" in mood or "drizzle" in mood:
        notes = [(392, 160), (330, 180), (294, 220), (330, 180)]
    elif "clear" in mood or "sun" in mood:
        notes = [(523, 120), (659, 120), (784, 180), (659, 120), (784, 220)]
    elif "cloud" in mood:
        notes = [(392, 160), (440, 160), (494, 200), (440, 200)]
    else:
        notes = [(440, 140), (523, 140), (587, 180), (523, 180)]

    try:
        Speaker.begin()
        try:
            Speaker.setVolumePercentage(SPEAKER_VOLUME_PERCENT)
        except Exception:
            pass
        for freq, duration in notes:
            try:
                Speaker.tone(freq, duration)
            except Exception:
                try:
                    Speaker.playTone(freq, duration)
                except Exception:
                    pass
            time.sleep_ms(duration + 40)
        try:
            Speaker.end()
        except Exception:
            pass
    except Exception:
        pass


def estimate_wav_seconds(audio_bytes):
    """Estimate WAV duration so TTS is not interrupted by music."""
    try:
        # Google Cloud TTS returns LINEAR16 WAV. In this project it is usually
        # 24 kHz, mono, 16-bit, so about 48 KB per second plus a tiny header.
        seconds = len(audio_bytes) // 48000
        if len(audio_bytes) % 48000:
            seconds += 1
        if seconds < 3:
            seconds = 3
        if seconds > 18:
            seconds = 18
        return seconds
    except Exception:
        pass
    return 8


def speak_text(text):
    global last_error, last_answer, answer_ready
    text = trim_sentence(text, 150)
    if not text:
        return False
    previous_answer = last_answer
    previous_ready = answer_ready
    last_answer = "Speaking..."
    answer_ready = False
    if UNDERTALE_UI:
        render_assistant(True)
    else:
        set_label(line1, "Speaking...", GREEN)
        set_label(line2, "", WHITE)
        set_label(line3, "Loading audio...", MUTED)
    try:
        response = requests.get(DEVICE_TTS_URL + "?text=" + url_encode(text), timeout=15)
        if response.status_code != 200:
            last_error = "TTS HTTP " + str(response.status_code)
            try:
                response.close()
            except Exception:
                pass
            last_answer = previous_answer
            answer_ready = previous_ready
            render_assistant(True)
            return False
        audio_path = "/flash/assistant.wav"
        audio_bytes = response.content
        with open(audio_path, "wb") as audio_file:
            audio_file.write(audio_bytes)
        try:
            response.close()
        except Exception:
            pass
        Speaker.begin()
        if not UNDERTALE_UI:
            set_label(line3, "Playing on Core2", GREEN)
        try:
            Speaker.setVolumePercentage(SPEAKER_VOLUME_PERCENT)
        except Exception:
            pass
        try:
            Speaker.playWAV(audio_path)
        except Exception:
            try:
                with open(audio_path, "rb") as audio_file:
                    raw = audio_file.read()
                Speaker.playRaw(raw, 24000)
            except Exception:
                pass
        time.sleep(estimate_wav_seconds(audio_bytes) + 1)
        try:
            Speaker.end()
        except Exception:
            pass
    except Exception as exc:
        last_error = "TTS " + str(exc)[:20]
        last_answer = previous_answer
        answer_ready = previous_ready
        return False
    last_answer = previous_answer
    answer_ready = previous_ready
    render_assistant(True)
    return True


def speak_answer():
    speak_text(last_answer)


def play_spotify_mood():
    global last_error
    if not SPOTIFY_MUSIC_ENABLED:
        return False
    if not UNDERTALE_UI:
        set_label(line1, "Spotify", GREEN)
        set_label(line2, "Starting playlist...", YELLOW)
        set_label(line3, trim(str(outdoor_main) + " " + str(outdoor_temp) + " C", 30), MUTED)
    try:
        url = (
            MUSIC_MOOD_URL
            + "?mood="
            + url_encode(outdoor_main)
            + "&temperature_c="
            + url_encode(outdoor_temp)
        )
        response = requests.get(url, timeout=SPOTIFY_TIMEOUT_SECONDS)
        ok = response.status_code >= 200 and response.status_code < 300
        if not ok:
            last_error = "Spotify HTTP " + str(response.status_code)
            try:
                if not UNDERTALE_UI:
                    set_label(line2, last_error, RED)
                    set_label(line3, trim(response.text, 32), MUTED)
            except Exception:
                pass
        try:
            response.close()
        except Exception:
            pass
        if ok:
            if not UNDERTALE_UI:
                set_label(line2, "Spotify started", GREEN)
            time.sleep(1)
        return ok
    except Exception as exc:
        last_error = "Spotify " + str(exc)[:18]
        if not UNDERTALE_UI:
            set_label(line2, "Spotify failed", RED)
            set_label(line3, trim(str(exc), 32), MUTED)
        time.sleep(2)
        return False


def run_morning_routine():
    global page, answer_ready, last_answer, last_transcript, last_error, last_morning_ms
    if not MORNING_ROUTINE_ENABLED:
        return
    if elapsed_ms(last_morning_ms) < MORNING_COOLDOWN_SECONDS * 1000:
        return

    last_morning_ms = now_ms()
    page = PAGE_ASSISTANT
    answer_ready = False
    last_transcript = ""
    last_answer = "Morning mode..."
    if UNDERTALE_UI:
        render_busy_screen("MORNING", "Motion detected", buddy)
    else:
        render_assistant(True)
    if not UNDERTALE_UI:
        set_label(line1, "Smart Home", GREEN)
        set_label(line2, "Motion detected", YELLOW)
        set_label(line3, "Preparing briefing...", MUTED)

    try:
        fetch_weather()
        fetch_forecast()
    except Exception:
        pass

    last_answer = get_ai_morning_briefing()
    answer_ready = True
    last_error = ""

    render_assistant(True)
    speak_text(last_answer)
    if not play_spotify_mood():
        if LOCAL_MUSIC_FALLBACK_ENABLED:
            play_mood_music(outdoor_main)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if UNDERTALE_UI:
    choose_wifi_on_boot()
connect_wifi()
init_sensors()
read_sensors()
send_sensor_reading()
fetch_weather()
fetch_forecast()
render(True)

last_send_ms = now_ms()
last_weather_ms = now_ms()
last_render_ms = now_ms()
last_button_ms = now_ms()
last_morning_ms = -MORNING_COOLDOWN_SECONDS * 1000

while True:
    M5.update()

    if elapsed_ms(last_button_ms) >= 350:
        raw_pressed = read_button_click()
        pressed = None
        if raw_pressed == BUTTON_PAGE:
            pressed = "PAGE"
        elif raw_pressed == BUTTON_NEXT:
            pressed = "NEXT"
        elif raw_pressed == BUTTON_ACTION:
            pressed = "ACTION"

        if pressed:
            last_button_ms = now_ms()

        if pressed == "PAGE":
            page = (page + 1) % 3
            render(True)

        elif pressed == "NEXT":
            if page == PAGE_DATA:
                set_label_on(status, "refresh", WHITE, HEADER)
                fetch_weather()
                fetch_forecast()
                send_sensor_reading()
                render(True)
            elif page == PAGE_ASSISTANT:
                question_index = (question_index + 1) % len(QUESTIONS)
                answer_ready = False
                last_answer = "Select a question."
                last_transcript = ""
                render(True)
            elif page == PAGE_FORECAST:
                set_label_on(status, "refresh", WHITE, 0x2563EB)
                fetch_forecast()
                render(True)
            elif UNDERTALE_UI and page == PAGE_WIFI:
                wifi_profile_index = (wifi_profile_index + 1) % len(wifi_profile_keys)
                render(True)
            elif UNDERTALE_UI and page == PAGE_CHARACTER:
                buddy.select((buddy.char_idx + 1) % len(CHARACTERS))
                render(True)

        elif pressed == "ACTION":
            if page == PAGE_ASSISTANT:
                current_question = QUESTIONS[question_index]
                if answer_ready:
                    speak_answer()
                elif current_question[2] == "VOICE_RECORD":
                    ask_by_voice()
                else:
                    ask_text(current_question[2])
            elif UNDERTALE_UI and page == PAGE_WIFI:
                apply_wifi_profile(wifi_profile_index)
                connect_wifi()
                fetch_weather()
                fetch_forecast()
                render(True)
            elif UNDERTALE_UI and page == PAGE_CHARACTER:
                buddy.select(buddy.char_idx)
                page = PAGE_DATA
                render(True)

    try:
        read_sensors()
    except Exception:
        pass

    if latest_motion and not previous_motion:
        run_morning_routine()
    previous_motion = latest_motion

    if elapsed_ms(last_send_ms) >= SEND_SECONDS * 1000:
        send_sensor_reading()
        last_send_ms = now_ms()
        if page == PAGE_DATA:
            render(False)

    if elapsed_ms(last_weather_ms) >= WEATHER_SECONDS * 1000:
        fetch_weather()
        fetch_forecast()
        last_weather_ms = now_ms()
        if page in (PAGE_DATA, PAGE_FORECAST):
            render(False)

    if elapsed_ms(last_render_ms) >= RENDER_SECONDS * 1000:
        last_render_ms = now_ms()
        if page == PAGE_DATA:
            render(False)

    time.sleep_ms(50)

