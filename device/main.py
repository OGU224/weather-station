"""M5Stack Core2 weather station firmware for UIFlow 2.

Final UIFlow 2 firmware. Copy it into UIFlow 2 as main.py. Keep real WiFi/API
values and local sensor mode in /flash/device_config.py on the Core2.

Buttons:
  A: switch page
  B: refresh on data page, next question on assistant page
  B long press: choose avatar
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

for _path in ("device/ui", "ui", "/flash", "/flash/ui"):
    try:
        if _path in sys.path:
            sys.path.remove(_path)
    except Exception:
        pass
for _path in ("/flash/ui", "/flash", "ui", "device/ui"):
    try:
        sys.path.insert(0, _path)
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
        PAGE_TREND,
        PAGE_WIFI,
        PAGE_CHARACTER,
        PAGE_COUNT,
    )
    UNDERTALE_UI = True
except Exception:
    UNDERTALE_UI = False

# ---------------------------------------------------------------------------
# WiFi/API setup.
# Real WiFi/API values live in /flash/device_config.py on the Core2.
# ---------------------------------------------------------------------------

DEFAULT_WIFI_PROFILES = {
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

DEFAULT_ACTIVE_PROFILE = "university"


def _load_wifi_config():
    profiles = DEFAULT_WIFI_PROFILES
    active = DEFAULT_ACTIVE_PROFILE

    try:
        import device_config
        custom_profiles = getattr(device_config, "WIFI_PROFILES", None)
        custom_active = getattr(device_config, "ACTIVE_PROFILE", None)
        if custom_profiles:
            profiles = custom_profiles
        if custom_active:
            active = custom_active
    except Exception:
        try:
            with open("/flash/wifi_profiles.json", "r") as config_file:
                data = ujson.loads(config_file.read())
            custom_profiles = data.get("profiles")
            if custom_profiles:
                profiles = custom_profiles
            custom_active = data.get("active_profile")
            if custom_active:
                active = custom_active
        except Exception:
            pass

    if active not in profiles:
        for key in profiles:
            active = key
            break
    return profiles, active


WIFI_PROFILES, ACTIVE_PROFILE = _load_wifi_config()
ACTIVE_WIFI = WIFI_PROFILES[ACTIVE_PROFILE]

WIFI_SSID = ACTIVE_WIFI["ssid"]
WIFI_PASSWORD = ACTIVE_WIFI["password"]
API_BASE_URL = ACTIVE_WIFI["api"]
DEVICE_ID = "m5stack-01"
SENSOR_MODE = "env3"  # "env3" for ENV III, "co2" for Unit TVOC/eCO2 on PORTA.

try:
    import device_config
    SENSOR_MODE = getattr(device_config, "SENSOR_MODE", SENSOR_MODE)
except Exception:
    pass

SEND_SECONDS = 60
WEATHER_SECONDS = 300
LOCATION_SECONDS = 1800
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
TIMEZONE_OFFSET_HOURS = 2
MORNING_QUESTION = (
    "Generate a very short smart-home briefing for someone who just entered "
    "the room. Adapt the greeting and clothing advice to the local time. "
    "Do not suggest sunglasses or sunscreen after sunset or in the evening. "
    "Use exactly this format with short phrases, no extra words: "
    "[Greeting]. Weather outside: [temperature] degrees, [weather]. "
    "Wear: [short clothing/accessory advice]."
)

# If physical buttons feel reversed after rotation, swap these labels only.
BUTTON_PAGE = "A"
BUTTON_NEXT = "B"
BUTTON_ACTION = "C"

API_BASE = API_BASE_URL.rstrip("/")
SENSOR_URL = API_BASE + "/api/sensors/reading"
LATEST_SENSOR_URL = API_BASE + "/api/sensors/latest?device_id="
LATEST_SENSOR_URL = LATEST_SENSOR_URL + DEVICE_ID
SENSOR_HISTORY_URL = API_BASE + "/api/sensors/history?device_id="
SENSOR_HISTORY_URL = SENSOR_HISTORY_URL + DEVICE_ID
SENSOR_HISTORY_URL = SENSOR_HISTORY_URL + "&hours=24"
WEATHER_URL = API_BASE + "/api/weather/current?device_id=" + DEVICE_ID
FORECAST_URL = API_BASE + "/api/weather/forecast?days=3&device_id=" + DEVICE_ID
ASK_URL = API_BASE + "/api/voice/ask"
DEVICE_ASK_URL = API_BASE + "/api/voice/device-audio-question"
DEVICE_TTS_URL = API_BASE + "/api/voice/device-tts"
MUSIC_MOOD_URL = API_BASE + "/api/music/play-mood"
LOCATION_WIFI_URL = API_BASE + "/api/location/wifi"


# ---------------------------------------------------------------------------
# UI constants/state
# ---------------------------------------------------------------------------

PAGE_DATA = 0
PAGE_FORECAST = 1
PAGE_ASSISTANT = 2
PAGE_TREND = 3
MAIN_PAGE_COUNT = 5 if UNDERTALE_UI else 4

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
clock_time = "--:--"
clock_date = "--/--"
clock_year = 0
clock_month = 0
clock_day = 0
clock_hour = 0
clock_minute = 0
clock_sync_ms = 0
sync_status = "No boot sync yet"
trend_temp_avg = "--"
trend_hum_avg = "--"
trend_motion_count = "--"
trend_co2 = "--"

env3 = None
co2_i2c = None


# Small compatibility helpers
#

def now_ms():
    return time.ticks_ms()


def elapsed_ms(start):
    return time.ticks_diff(time.ticks_ms(), start)


def _is_leap_year(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _month_days(year, month):
    if month == 2:
        return 29 if _is_leap_year(year) else 28
    if month in (4, 6, 9, 11):
        return 30
    return 31


def set_clock_from_iso(timestamp):
    global clock_time, clock_date, clock_year, clock_month, clock_day, clock_hour, clock_minute, clock_sync_ms
    try:
        text = str(timestamp or "")
        year = int(text[0:4])
        month = int(text[5:7])
        day = int(text[8:10])
        hour = int(text[11:13]) + TIMEZONE_OFFSET_HOURS
        minute = int(text[14:16])

        if hour >= 24:
            hour -= 24
            day += 1
            if day > _month_days(year, month):
                day = 1
                month += 1
                if month > 12:
                    month = 1
                    year += 1

        if hour < 0:
            hour += 24
            day -= 1
            if day < 1:
                month -= 1
                if month < 1:
                    month = 12
                    year -= 1
                day = _month_days(year, month)

        clock_year = year
        clock_month = month
        clock_day = day
        clock_hour = hour
        clock_minute = minute
        clock_sync_ms = now_ms()
        refresh_clock_display()
    except Exception:
        pass


def refresh_clock_display():
    global clock_time, clock_date
    if clock_year <= 0 or clock_month <= 0 or clock_day <= 0:
        return
    try:
        elapsed_minutes = 0
        if clock_sync_ms:
            elapsed_minutes = elapsed_ms(clock_sync_ms) // 60000
        year = clock_year
        month = clock_month
        day = clock_day
        total_minutes = clock_hour * 60 + clock_minute + elapsed_minutes
        while total_minutes >= 1440:
            total_minutes -= 1440
            day += 1
            if day > _month_days(year, month):
                day = 1
                month += 1
                if month > 12:
                    month = 1
                    year += 1
        hour = total_minutes // 60
        minute = total_minutes % 60
        clock_time = "{:02d}:{:02d}".format(hour, minute)
        clock_date = "{:02d}/{:02d}".format(month, day)
    except Exception:
        pass


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
    cleaned = ""
    for char in text:
        if ord(char) < 128:
            cleaned += char
    return cleaned


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
    for word in keywords:
        if word in value:
            return True
    return False


def local_hour():
    try:
        if clock_time and clock_time != "--:--":
            return int(str(clock_time)[0:2])
    except Exception:
        pass
    return None


def is_daylight_hour():
    hour = local_hour()
    if hour is None:
        return True
    return hour >= 7 and hour < 19


def smart_greeting():
    hour = local_hour()
    if hour is None or hour < 12:
        return "Good morning"
    if hour < 18:
        return "Good afternoon"
    return "Good evening"


def local_outfit_advice():
    weather = str(outdoor_main or "").lower()
    try:
        temp = float(outdoor_temp)
    except Exception:
        temp = None

    if "rain" in weather or "drizzle" in weather or "storm" in weather:
        return "Don't forget an umbrella or a rain jacket."
    if temp is not None and temp >= 24:
        if is_daylight_hour():
            return "Wear light clothes, and bring sunglasses."
        return "Wear light clothes for the warm evening."
    if ("clear" in weather or "sun" in weather) and is_daylight_hour():
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
    city = str(outdoor_city or "outside")
    return (
        "Outside in "
        + city
        + ", it is "
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
        return smart_greeting() + ". Weather outside: unavailable. Wear: take a light layer just in case."
    return (
        smart_greeting()
        + ". Weather outside: "
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
        + " Local time: "
        + str(clock_time)
        + ". Local date: "
        + str(clock_date)
        + ". Current outdoor data: city "
        + str(outdoor_city or "outside")
        + ", temperature "
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
    greeting_ok = "good morning" in value or "good afternoon" in value or "good evening" in value or "hello" in value
    if not greeting_ok:
        return False
    weather_ok = "weather outside" in value or str(outdoor_temp).lower() in value
    if not weather_ok:
        return False
    if not is_daylight_hour() and ("sunglasses" in value or "sunscreen" in value):
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


LONG_PRESS_MS = 900
last_a_down = False
last_b_down = False
last_c_down = False
b_down_ms = 0
b_long_sent = False


def read_button_event():
    global last_a_down, last_b_down, last_c_down, b_down_ms, b_long_sent

    a_down = button_is_down(BtnA)
    b_down = button_is_down(BtnB)
    c_down = button_is_down(BtnC)

    if b_down and not last_b_down:
        b_down_ms = now_ms()
        b_long_sent = False

    event = None
    if c_down and not last_c_down:
        event = "C"
    elif b_down and not b_long_sent and elapsed_ms(b_down_ms) >= LONG_PRESS_MS:
        b_long_sent = True
        event = "B_LONG"
    elif not b_down and last_b_down and not b_long_sent:
        event = "B"
    elif a_down and not last_a_down:
        event = "A"

    last_a_down = a_down
    last_b_down = b_down
    last_c_down = c_down
    return event


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
        refresh_clock_display()
        return {
            "temp": latest_temp,
            "hum": latest_hum,
            "co2": latest_co2,
            "sensor_mode": SENSOR_MODE,
            "send_ok": send_ok,
            "o_temp": outdoor_temp,
            "o_hum": outdoor_hum,
            "o_main": outdoor_main,
            "o_icon": "",
            "o_ok": outdoor_ok,
            "fcast": forecast_days,
            "tstr": clock_time,
            "dstr": clock_date,
            "qi": question_index,
            "ans_ok": answer_ready,
            "ans_txt": _ui_answer_text(),
            "wifi_profiles": _ui_wifi_profiles(),
            "wifi_idx": wifi_profile_index,
            "wifi_status": wifi_status,
            "char_idx": buddy.char_idx,
            "sync_status": sync_status,
            "trend_temp": trend_temp_avg,
            "trend_hum": trend_hum_avg,
            "trend_motion": trend_motion_count,
            "trend_co2": trend_co2,
        }

    def render_data(full=True):
        render_undertale(PAGE_DATA, _ui_state(), buddy, full)

    def render_forecast(full=True):
        render_undertale(PAGE_FORECAST, _ui_state(), buddy, full)

    def render_assistant(full=True):
        render_undertale(PAGE_ASSISTANT, _ui_state(), buddy, full)

    def render_trend(full=True):
        render_undertale(PAGE_TREND, _ui_state(), buddy, full)

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
        elif page == PAGE_TREND:
            render_trend(full)
        elif page == PAGE_WIFI:
            render_wifi(full)
        elif page == PAGE_CHARACTER:
            render_character(full)

    def apply_wifi_profile(index):
        global WIFI_SSID, WIFI_PASSWORD, API_BASE_URL, API_BASE
        global SENSOR_URL, WEATHER_URL, FORECAST_URL, ASK_URL, DEVICE_ASK_URL
        global DEVICE_TTS_URL, MUSIC_MOOD_URL, ACTIVE_PROFILE, ACTIVE_WIFI
        global LATEST_SENSOR_URL, SENSOR_HISTORY_URL, LOCATION_WIFI_URL

        key = wifi_profile_keys[index]
        ACTIVE_PROFILE = key
        ACTIVE_WIFI = WIFI_PROFILES[key]
        WIFI_SSID = ACTIVE_WIFI["ssid"]
        WIFI_PASSWORD = ACTIVE_WIFI["password"]
        API_BASE_URL = ACTIVE_WIFI["api"]
        API_BASE = API_BASE_URL.rstrip("/")
        SENSOR_URL = API_BASE + "/api/sensors/reading"
        LATEST_SENSOR_URL = API_BASE + "/api/sensors/latest?device_id=" + DEVICE_ID
        SENSOR_HISTORY_URL = API_BASE + "/api/sensors/history?device_id=" + DEVICE_ID + "&hours=24"
        WEATHER_URL = API_BASE + "/api/weather/current?device_id=" + DEVICE_ID
        FORECAST_URL = API_BASE + "/api/weather/forecast?days=3&device_id=" + DEVICE_ID
        ASK_URL = API_BASE + "/api/voice/ask"
        DEVICE_ASK_URL = API_BASE + "/api/voice/device-audio-question"
        DEVICE_TTS_URL = API_BASE + "/api/voice/device-tts"
        MUSIC_MOOD_URL = API_BASE + "/api/music/play-mood"
        LOCATION_WIFI_URL = API_BASE + "/api/location/wifi"

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
    if UNDERTALE_UI:
        wifi_status = "Connecting to " + WIFI_SSID
        render_wifi(True)
    else:
        draw_base("WiFi", HEADER)
        set_label(line1, "Connecting...", BLUE)
        set_label(line2, WIFI_SSID, WHITE)
        set_label(line3, "Resetting WiFi", MUTED)

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
                    else:
                        set_label(line3, "Connected", GREEN)
                    time.sleep(1)
                except Exception:
                    pass
                return True
            if UNDERTALE_UI:
                wifi_status = "Waiting " + str(_ + 1) + "/30"
                render_wifi(False)
            else:
                set_label(line3, "Waiting " + str(_ + 1) + "/30", MUTED)
            time.sleep(1)
    except Exception as exc:
        last_error = "WiFi " + str(exc)[:20]

    wifi_ok = False
    if UNDERTALE_UI:
        wifi_status = "Failed: " + trim(last_error, 20)
        render_wifi(True)
    else:
        set_label(line3, "WiFi failed", RED)
        set_label(line4, trim(last_error, 28), RED)
    time.sleep(2)
    return False


def _bssid_to_mac(bssid):
    try:
        values = []
        for byte in bssid:
            if isinstance(byte, str):
                byte = ord(byte)
            values.append("%02x" % int(byte))
        if len(values) == 6:
            return ":".join(values)
    except Exception:
        pass
    return ""


def submit_wifi_location():
    global last_error
    if network is None:
        return False

    try:
        wlan = network.WLAN(network.STA_IF)
        if not wlan.active():
            wlan.active(True)
        scan_rows = wlan.scan()
    except Exception as exc:
        last_error = "WiFi scan " + str(exc)[:12]
        return False

    access_points = []
    for row in scan_rows:
        try:
            bssid = row[1]
            channel = row[2]
            rssi = row[3]
            mac = _bssid_to_mac(bssid)
            if mac:
                access_points.append({
                    "macAddress": mac,
                    "signalStrength": int(rssi),
                    "channel": int(channel),
                })
        except Exception:
            pass
        if len(access_points) >= 12:
            break

    if len(access_points) < 2:
        last_error = "Location needs WiFi"
        return False

    try:
        response = requests.post(
            LOCATION_WIFI_URL,
            json={
                "device_id": DEVICE_ID,
                "wifiAccessPoints": access_points,
            },
            headers={"Content-Type": "application/json"},
            timeout=8,
        )
        ok = response.status_code >= 200 and response.status_code < 300
        if not ok:
            last_error = "Location HTTP " + str(response.status_code)
        try:
            response.close()
        except Exception:
            pass
        return ok
    except Exception as exc:
        last_error = "Location " + str(exc)[:15]
        return False


def init_sensors():
    global env3, co2_i2c, last_error
    if I2C is None or Pin is None:
        last_error = "I2C unavailable"
        return

    if SENSOR_MODE == "co2":
        try:
            co2_i2c = I2C(0, scl=Pin(33), sda=Pin(32), freq=100000)
            _sgp30_write_command(0x2003)
            time.sleep_ms(50)
            last_error = ""
        except Exception as exc:
            co2_i2c = None
            last_error = "CO2 " + str(exc)[:18]
        return

    if ENVUnit is not None:
        try:
            i2c0 = I2C(0, scl=Pin(33), sda=Pin(32), freq=100000)
            env3 = ENVUnit(i2c=i2c0, type=3)
        except Exception as exc:
            env3 = None
            last_error = "ENV " + str(exc)[:18]


def _sgp30_write_command(command):
    if co2_i2c is not None:
        co2_i2c.writeto(0x58, bytearray([(command >> 8) & 0xFF, command & 0xFF]))


def _sgp30_read_co2_tvoc():
    if co2_i2c is None:
        return None, None
    _sgp30_write_command(0x2008)
    time.sleep_ms(20)
    data = co2_i2c.readfrom(0x58, 6)
    co2 = (data[0] << 8) | data[1]
    tvoc = (data[3] << 8) | data[4]
    return co2, tvoc


def read_sensors():
    global latest_temp, latest_hum, latest_motion, latest_co2, last_error
    if SENSOR_MODE == "co2":
        try:
            co2, tvoc = _sgp30_read_co2_tvoc()
            if co2 is not None:
                latest_co2 = int(co2)
                last_error = "TVOC " + str(tvoc) + " ppb"
        except Exception as exc:
            last_error = "CO2 read " + str(exc)[:14]
    elif env3 is not None:
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
    temp_payload = latest_temp
    hum_payload = latest_hum
    if SENSOR_MODE == "co2":
        temp_payload = None
        hum_payload = None

    payload = {
        "device_id": DEVICE_ID,
        "temperature_c": temp_payload,
        "humidity_percent": hum_payload,
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


def fetch_latest_sensor_reading():
    global latest_temp, latest_hum, latest_motion, latest_co2, sync_status, last_error
    try:
        response = requests.get(LATEST_SENSOR_URL, timeout=5)
        if response.status_code == 200:
            data = get_json_response(response)
            temp = data.get("temperature_c")
            hum = data.get("humidity_pct")
            co2 = data.get("air_quality_index")
            if temp is not None:
                latest_temp = round(float(temp), 1)
            if hum is not None:
                latest_hum = round(float(hum), 1)
            if co2 is not None:
                latest_co2 = int(float(co2))
            latest_motion = bool(data.get("motion_detected", False))
            ts = str(data.get("timestamp") or "")
            sync_status = "Synced " + (ts[11:16] if len(ts) >= 16 else "latest")
            return True
        sync_status = "No saved reading"
    except Exception as exc:
        sync_status = "Sync failed"
        last_error = "Sync " + str(exc)[:18]
    return False


def fetch_sensor_trend():
    global trend_temp_avg, trend_hum_avg, trend_motion_count, trend_co2
    try:
        response = requests.get(SENSOR_HISTORY_URL, timeout=6)
        if response.status_code != 200:
            return False
        rows = get_json_response(response)
        temp_sum = 0
        temp_count = 0
        hum_sum = 0
        hum_count = 0
        motion_count = 0
        last_co2 = None
        for row in rows:
            temp = row.get("temperature_c")
            hum = row.get("humidity_pct")
            co2 = row.get("air_quality_index")
            if temp is not None:
                temp_sum += float(temp)
                temp_count += 1
            if hum is not None:
                hum_sum += float(hum)
                hum_count += 1
            if row.get("motion_detected"):
                motion_count += 1
            if co2 is not None:
                last_co2 = int(float(co2))
        trend_temp_avg = str(round(temp_sum / temp_count, 1)) if temp_count else "--"
        trend_hum_avg = str(round(hum_sum / hum_count, 1)) if hum_count else "--"
        trend_motion_count = str(motion_count)
        trend_co2 = (str(last_co2) + " ppm") if last_co2 is not None else "not measured"
        return True
    except Exception:
        return False


def fetch_weather():
    global outdoor_ok, outdoor_temp, outdoor_hum, outdoor_wind, outdoor_main, outdoor_city, last_error
    try:
        response = requests.get(WEATHER_URL, timeout=5)
        if response.status_code == 200:
            data = get_json_response(response)
            set_clock_from_iso(data.get("timestamp"))
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
submit_wifi_location()
fetch_latest_sensor_reading()
init_sensors()
read_sensors()
send_sensor_reading()
fetch_weather()
fetch_forecast()
fetch_sensor_trend()
render(True)

last_send_ms = now_ms()
last_weather_ms = now_ms()
last_location_ms = now_ms()
last_render_ms = now_ms()
last_button_ms = now_ms()
last_morning_ms = -MORNING_COOLDOWN_SECONDS * 1000

while True:
    M5.update()

    if elapsed_ms(last_button_ms) >= 350:
        raw_pressed = read_button_event()
        pressed = None
        if raw_pressed == BUTTON_PAGE:
            pressed = "PAGE"
        elif raw_pressed == BUTTON_NEXT:
            pressed = "NEXT"
        elif raw_pressed == BUTTON_ACTION:
            pressed = "ACTION"
        elif raw_pressed == "B_LONG":
            pressed = "CHARACTER"

        if pressed:
            last_button_ms = now_ms()

        if pressed == "PAGE":
            if UNDERTALE_UI and page == PAGE_CHARACTER:
                page = PAGE_DATA
            else:
                page = (page + 1) % MAIN_PAGE_COUNT
            render(True)

        elif pressed == "CHARACTER" and UNDERTALE_UI:
            page = PAGE_CHARACTER
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
            elif page == PAGE_TREND:
                fetch_latest_sensor_reading()
                fetch_sensor_trend()
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
                submit_wifi_location()
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

    if MORNING_ROUTINE_ENABLED and latest_motion and not previous_motion:
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
        fetch_sensor_trend()
        last_weather_ms = now_ms()
        if page == PAGE_DATA or page == PAGE_FORECAST or page == PAGE_TREND:
            render(False)

    if elapsed_ms(last_location_ms) >= LOCATION_SECONDS * 1000:
        submit_wifi_location()
        last_location_ms = now_ms()

    if elapsed_ms(last_render_ms) >= RENDER_SECONDS * 1000:
        last_render_ms = now_ms()
        if page == PAGE_DATA:
            render(False)

    time.sleep_ms(50)
