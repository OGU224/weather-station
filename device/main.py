"""M5Stack Core2 weather station with a small assistant page.

Buttons:
  A: switch between data, forecast, and assistant pages
  B: on assistant page, cycle suggested questions
  C: on assistant page, ask the selected question or speak the answer
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
# Change ACTIVE_PROFILE when you move between hotspot and university WiFi.
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

}

ACTIVE_PROFILE = "hotspot"
ACTIVE_WIFI = WIFI_PROFILES[ACTIVE_PROFILE]

WIFI_SSID = ACTIVE_WIFI["ssid"]
WIFI_PASSWORD = ACTIVE_WIFI["password"]
API_BASE_URL = ACTIVE_WIFI["api"]
DEVICE_ID = "m5stack-01"
SENSOR_MODE = "env3"  # "env3" for temperature/humidity, "co2" when the CO2 unit is plugged into PORTA.
SEND_INTERVAL_SECONDS = 60
WEATHER_REFRESH_SECONDS = 300
DATA_RENDER_SECONDS = 15
SPEAKER_VOLUME = 12

API_BASE = API_BASE_URL.rstrip("/")
SENSOR_URL = API_BASE + "/api/sensors/reading"
WEATHER_URL = API_BASE + "/api/weather/current"
FORECAST_URL = API_BASE + "/api/weather/forecast?days=3"
ASK_URL = API_BASE + "/api/voice/ask"
DEVICE_SUMMARY_URL = API_BASE + "/api/voice/device-summary"
TTS_URL = API_BASE + "/api/voice/tts"
DEVICE_TTS_URL = API_BASE + "/api/voice/device-tts"

PAGE_DATA = 0
PAGE_FORECAST = 1
PAGE_ASSISTANT = 2

QUESTIONS = [
    (
        "Comfort now",
        "Check room comfort",
        "Check comfort using indoor and outdoor weather. Answer in at most 18 words.",
    ),
    (
        "Ventilate?",
        "Open window now?",
        "Should I open the window now? Answer in at most 18 words.",
    ),
    (
        "Humidity",
        "Is humidity OK?",
        "Is the room humidity healthy today? Answer in at most 18 words.",
    ),
    (
        "Outside",
        "Weather outside",
        "Summarize outdoor weather and forecast. Answer in at most 18 words.",
    ),
    (
        "Motion",
        "Motion today",
        "Summarize motion activity today. Answer in at most 18 words.",
    ),
]

current_page = PAGE_DATA
pending_action = None
selected_question = 0
answer_ready = False
last_answer = "Select a question."
last_speech = ""
last_send_ok = False
last_send_ms = 0
last_weather_ms = 0
last_render_ms = 0
latest_temp = 0.0
latest_hum = 0.0
latest_motion = False
latest_co2 = None
outdoor_temp = "--"
outdoor_hum = "--"
outdoor_wind = "--"
outdoor_main = "Weather"
outdoor_city = "Outdoor"
outdoor_ok = False
outdoor_status = "loading"
forecast_days = []
forecast_ok = False
forecast_status = "loading"
wifi_connected = False


BG = 0x101827
PANEL = 0x1F2937
PANEL_2 = 0x263445
TEXT = 0xFFFFFF
MUTED = 0xA7B3C6
BLUE = 0x38BDF8
GREEN = 0x34D399
YELLOW = 0xFBBF24
RED = 0xF87171

setScreenColor(BG)
lcd.clear()
lcd.font(lcd.FONT_Default)

title = M5TextBox(10, 10, "Weather Station", lcd.FONT_Default, 0xFFFFFF)
line1 = M5TextBox(10, 38, "", lcd.FONT_Default, TEXT)
line2 = M5TextBox(10, 66, "", lcd.FONT_Default, TEXT)
line3 = M5TextBox(10, 94, "", lcd.FONT_Default, TEXT)
line4 = M5TextBox(10, 122, "", lcd.FONT_Default, TEXT)
line5 = M5TextBox(10, 150, "", lcd.FONT_Default, TEXT)
line6 = M5TextBox(10, 178, "", lcd.FONT_Default, TEXT)
status_line = M5TextBox(10, 178, "", lcd.FONT_Default, MUTED)
footer = M5TextBox(10, 214, "A: page", lcd.FONT_Default, 0xAAAAAA)


def set_lines(a="", b="", c="", d="", e="", f=""):
    line1.setText(str(a))
    line2.setText(str(b))
    line3.setText(str(c))
    line4.setText(str(d))
    line5.setText(str(e))
    line6.setText(str(f))


def clear_texts():
    set_lines("", "", "", "", "", "")
    status_line.setText("")
    footer.setText("")


def set_text_color(widget, color):
    try:
        widget.setColor(color)
    except Exception:
        pass


def move_text(widget, x, y):
    try:
        widget.setPosition(x, y)
    except Exception:
        pass


def use_full_text_layout():
    move_text(title, 14, 11)
    move_text(line1, 18, 48)
    move_text(line2, 18, 76)
    move_text(line3, 18, 104)
    move_text(line4, 18, 132)
    move_text(line5, 18, 160)
    move_text(line6, 18, 188)
    move_text(status_line, 10, 196)
    move_text(footer, 10, 214)


def use_dashboard_text_layout():
    move_text(title, 10, 9)
    move_text(line1, 18, 48)
    move_text(line2, 18, 76)
    move_text(line3, 18, 112)
    move_text(line4, 178, 48)
    move_text(line5, 178, 76)
    move_text(line6, 178, 112)
    move_text(status_line, 18, 171)
    move_text(footer, 10, 214)


def use_forecast_text_layout():
    move_text(title, 10, 9)
    move_text(line1, 18, 50)
    move_text(line2, 18, 70)
    move_text(line3, 18, 108)
    move_text(line4, 18, 128)
    move_text(line5, 18, 166)
    move_text(line6, 18, 186)
    move_text(status_line, 170, 166)
    move_text(footer, 10, 214)


def use_assistant_text_layout():
    move_text(title, 14, 11)
    move_text(line1, 34, 62)
    move_text(line2, 34, 102)
    move_text(line3, 34, 132)
    move_text(line4, 24, 162)
    move_text(line5, 24, 184)
    move_text(line6, 24, 188)
    move_text(status_line, 10, 196)
    move_text(footer, 10, 214)


def fill_rect(x, y, w, h, color):
    try:
        lcd.rect(x, y, w, h, color, color)
    except Exception:
        try:
            lcd.fillRect(x, y, w, h, color)
        except Exception:
            pass


def draw_circle(x, y, r, color):
    try:
        lcd.circle(x, y, r, color, color)
    except Exception:
        try:
            lcd.circle(x, y, r, color)
        except Exception:
            pass


def draw_line(x1, y1, x2, y2, color):
    try:
        lcd.line(x1, y1, x2, y2, color)
    except Exception:
        pass


def draw_weather_icon(main, x, y):
    condition = str(main).lower()
    if "rain" in condition or "drizzle" in condition:
        draw_circle(x, y, 16, 0x94A3B8)
        draw_circle(x - 15, y + 4, 11, 0x94A3B8)
        draw_circle(x + 15, y + 5, 11, 0x94A3B8)
        draw_line(x - 16, y + 28, x - 22, y + 38, BLUE)
        draw_line(x, y + 28, x - 6, y + 38, BLUE)
        draw_line(x + 16, y + 28, x + 10, y + 38, BLUE)
    elif "cloud" in condition:
        draw_circle(x, y, 17, 0xCBD5E1)
        draw_circle(x - 16, y + 5, 11, 0xCBD5E1)
        draw_circle(x + 17, y + 6, 11, 0xCBD5E1)
        fill_rect(x - 23, y + 5, 47, 14, 0xCBD5E1)
    elif "snow" in condition:
        draw_circle(x, y, 16, 0xE0F2FE)
        draw_line(x - 18, y + 30, x + 18, y + 30, TEXT)
        draw_line(x, y + 14, x, y + 46, TEXT)
        draw_line(x - 12, y + 18, x + 12, y + 42, TEXT)
        draw_line(x + 12, y + 18, x - 12, y + 42, TEXT)
    else:
        draw_circle(x, y + 8, 19, YELLOW)
        draw_line(x, y - 20, x, y - 30, YELLOW)
        draw_line(x, y + 39, x, y + 49, YELLOW)
        draw_line(x - 29, y + 8, x - 40, y + 8, YELLOW)
        draw_line(x + 29, y + 8, x + 40, y + 8, YELLOW)


def draw_mini_weather_icon(main, x, y):
    condition = str(main).lower()
    if "rain" in condition or "drizzle" in condition:
        draw_circle(x, y, 8, 0xCBD5E1)
        draw_circle(x - 8, y + 3, 6, 0xCBD5E1)
        draw_circle(x + 8, y + 3, 6, 0xCBD5E1)
        draw_line(x - 7, y + 14, x - 10, y + 20, BLUE)
        draw_line(x + 4, y + 14, x + 1, y + 20, BLUE)
    elif "cloud" in condition:
        draw_circle(x, y, 9, 0xCBD5E1)
        draw_circle(x - 9, y + 3, 6, 0xCBD5E1)
        draw_circle(x + 9, y + 3, 6, 0xCBD5E1)
        fill_rect(x - 13, y + 3, 27, 8, 0xCBD5E1)
    else:
        draw_circle(x, y, 11, YELLOW)
        draw_line(x, y - 15, x, y - 20, YELLOW)
        draw_line(x, y + 15, x, y + 20, YELLOW)
        draw_line(x - 15, y, x - 20, y, YELLOW)
        draw_line(x + 15, y, x + 20, y, YELLOW)


def draw_data_frame():
    clear_texts()
    fill_rect(0, 0, 320, 240, BG)
    fill_rect(0, 0, 320, 30, 0x0F766E)
    fill_rect(8, 38, 144, 112, PANEL)
    fill_rect(168, 38, 144, 112, PANEL)
    fill_rect(8, 158, 304, 40, PANEL_2)
    fill_rect(0, 204, 320, 36, 0x0B1220)
    if outdoor_ok:
        draw_mini_weather_icon(outdoor_main, 286, 62)


def draw_question_frame():
    clear_texts()
    fill_rect(0, 0, 320, 240, BG)
    fill_rect(0, 0, 320, 32, 0x4338CA)
    fill_rect(14, 48, 292, 110, PANEL_2)
    fill_rect(0, 204, 320, 36, 0x0B1220)
    fill_rect(22, 58, 4, 88, BLUE)


def draw_answer_frame():
    clear_texts()
    fill_rect(0, 0, 320, 240, BG)
    fill_rect(0, 0, 320, 32, 0x0F766E)
    fill_rect(10, 44, 300, 148, PANEL)
    fill_rect(0, 204, 320, 36, 0x0B1220)
    draw_circle(286, 61, 12, GREEN)


def draw_forecast_frame():
    clear_texts()
    fill_rect(0, 0, 320, 240, BG)
    fill_rect(0, 0, 320, 30, 0x0369A1)
    fill_rect(8, 40, 304, 44, PANEL)
    fill_rect(8, 98, 304, 44, PANEL)
    fill_rect(8, 156, 304, 44, PANEL)
    fill_rect(0, 204, 320, 36, 0x0B1220)


def short_date(date_text):
    text = str(date_text)
    if len(text) >= 10:
        return text[5:10]
    return text


def forecast_line(index):
    if not forecast_ok or index >= len(forecast_days):
        return "--", forecast_status
    item = forecast_days[index]
    date_text = short_date(item.get("date", "day"))
    low = str(round(float(item.get("temp_min", 0)), 1))
    high = str(round(float(item.get("temp_max", 0)), 1))
    condition = str(item.get("weather_main", "Weather"))
    if "Rain" in condition:
        condition = "Rain expected"
    elif "Cloud" in condition:
        condition = "Cloudy"
    elif "Clear" in condition:
        condition = "Clear sky"
    elif "Snow" in condition:
        condition = "Snow"
    return date_text + "   " + high + "/" + low + " C", condition


def current_alert():
    if latest_hum and latest_hum < 40:
        return "Low humidity", YELLOW
    if latest_hum and latest_hum > 65:
        return "Humid room", YELLOW
    if latest_motion:
        return "Motion now", BLUE
    if outdoor_ok and ("rain" in str(outdoor_main).lower() or "drizzle" in str(outdoor_main).lower()):
        return "Rain outside", BLUE
    if last_send_ok:
        return "All good", GREEN
    return "Waiting upload", MUTED


def short_lines(text, max_chars=31, max_lines=6):
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


def display_value(value, suffix=""):
    if value is None:
        return "--"
    return str(value) + suffix


def fit_answer(text, max_chars=135):
    value = str(text).replace("\n", " ").strip()
    if len(value) > max_chars:
        value = value[: max_chars - 3].rstrip() + "..."
    return value


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
    use_dashboard_text_layout()
    draw_data_frame()
    title.setText("Cloud Weather")
    set_text_color(title, TEXT)
    wifi_text = "connected" if wifi_connected else "not connected"
    upload_text = "BQ ok" if last_send_ok else "BQ wait"
    weather_text = outdoor_main if outdoor_ok else outdoor_status
    set_lines(
        "INDOOR",
        display_value(latest_temp, " C") + "   " + display_value(latest_hum, "%"),
        "Motion: " + ("yes" if latest_motion else "no"),
        "OUTDOOR",
        str(outdoor_temp) + " C   " + str(outdoor_hum) + "%",
        str(weather_text),
    )
    if SENSOR_MODE == "co2":
        line2.setText("CO2 " + display_value(latest_co2, " ppm"))
    set_text_color(line1, BLUE)
    set_text_color(line2, TEXT)
    set_text_color(line3, MUTED)
    set_text_color(line4, GREEN)
    set_text_color(line5, TEXT)
    set_text_color(line6, MUTED)
    footer.setText("A: Forecast")
    alert_text, alert_color = current_alert()
    status_line.setText(alert_text + "    " + upload_text)
    set_text_color(status_line, alert_color)
    set_text_color(footer, MUTED)


def reset_text_colors():
    set_text_color(title, TEXT)
    set_text_color(line1, TEXT)
    set_text_color(line2, TEXT)
    set_text_color(line3, TEXT)
    set_text_color(line4, TEXT)
    set_text_color(line5, TEXT)
    set_text_color(line6, TEXT)
    set_text_color(status_line, MUTED)
    set_text_color(footer, MUTED)


def render_question_page():
    use_assistant_text_layout()
    draw_question_frame()
    reset_text_colors()
    title.setText("Ask Assistant")
    item = QUESTIONS[selected_question]
    lines = short_lines(item[1], 28, 1)
    set_lines(
        item[0],
        lines[0],
        "",
        "",
        "",
        "",
    )
    set_text_color(line1, BLUE)
    set_text_color(line2, TEXT)
    set_text_color(line3, TEXT)
    set_text_color(line4, MUTED)
    footer.setText("A:data     B:next     C:ask")


def render_forecast_page():
    use_forecast_text_layout()
    draw_forecast_frame()
    reset_text_colors()
    title.setText("Forecast")
    d0, t0 = forecast_line(0)
    d1, t1 = forecast_line(1)
    d2, t2 = forecast_line(2)
    set_lines(d0, t0, d1, t1, d2, t2)
    set_text_color(line1, BLUE)
    set_text_color(line2, MUTED)
    set_text_color(line3, BLUE)
    set_text_color(line4, MUTED)
    set_text_color(line5, BLUE)
    set_text_color(line6, MUTED)
    footer.setText("A: Assistant")


def render_assistant_page():
    if not answer_ready:
        render_question_page()
        return

    use_full_text_layout()
    draw_answer_frame()
    reset_text_colors()
    title.setText("Answer")
    lines = short_lines(fit_answer(last_answer, 115), 29, 4)
    set_lines(
        QUESTIONS[selected_question][0],
        lines[0],
        lines[1],
        lines[2],
        lines[3],
        "",
    )
    set_text_color(line1, GREEN)
    footer.setText("A:data  B:next  C:speak")


def render_page():
    if current_page == PAGE_ASSISTANT:
        render_assistant_page()
    elif current_page == PAGE_FORECAST:
        render_forecast_page()
    else:
        render_sensor_page()


def connect_wifi():
    global wifi_connected
    if not WIFI_SSID or not WIFI_PASSWORD:
        wifi_connected = False
        set_lines("WiFi config missing", "Check ACTIVE_PROFILE")
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


def init_co2():
    try:
        return unit.get(unit.TVOC, unit.PORTA)
    except Exception:
        try:
            return unit.get(unit.CO2, unit.PORTA)
        except Exception:
            return None


def read_co2(co2_sensor):
    if not co2_sensor:
        return None

    for attr in ["co2", "co2_ppm", "eCO2", "eco2", "CO2"]:
        try:
            value = getattr(co2_sensor, attr)
            if value is not None:
                return int(float(value))
        except Exception:
            pass
    return None


def read_sensors(env3_sensor, pir_sensor, co2_sensor):
    temp = None
    hum = None
    co2 = None
    motion = False

    if SENSOR_MODE == "env3" and env3_sensor:
        temp = round(float(env3_sensor.temperature), 1)
        hum = round(float(env3_sensor.humidity), 1)

    if SENSOR_MODE == "co2":
        co2 = read_co2(co2_sensor)

    if pir_sensor:
        motion = True if pir_sensor.state == 1 else False

    return temp, hum, motion, co2


def send_data_to_api(temp, hum, motion, co2):
    payload = {
        "device_id": DEVICE_ID,
        "temperature_c": temp,
        "humidity_percent": hum,
        "motion_detected": motion,
        "co2_source": "sensor" if co2 is not None else "not measured",
    }
    if co2 is not None:
        payload["co2_ppm"] = co2

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


def fetch_outdoor_weather():
    global outdoor_temp, outdoor_hum, outdoor_wind, outdoor_main, outdoor_city, outdoor_ok, outdoor_status
    try:
        response = urequests.get(WEATHER_URL)
        if response.status_code < 200 or response.status_code >= 300:
            status_code = response.status_code
            response.close()
            outdoor_ok = False
            outdoor_status = "HTTP " + str(status_code)
            return False
        data = response.json()
        response.close()
        outdoor_temp = str(round(float(data.get("temperature_c", 0)), 1))
        outdoor_hum = str(int(data.get("humidity_pct", 0)))
        outdoor_wind = str(round(float(data.get("wind_speed_ms", 0)), 1))
        outdoor_main = str(data.get("weather_main", "Weather"))
        outdoor_city = str(data.get("city", "Outdoor"))
        outdoor_ok = True
        outdoor_status = "online"
        return True
    except Exception:
        outdoor_ok = False
        outdoor_status = "request failed"
        return False


def fetch_forecast():
    global forecast_days, forecast_ok, forecast_status
    try:
        response = urequests.get(FORECAST_URL)
        if response.status_code < 200 or response.status_code >= 300:
            status_code = response.status_code
            response.close()
            forecast_ok = False
            forecast_status = "HTTP " + str(status_code)
            return False
        forecast_days = response.json()
        response.close()
        forecast_ok = True
        forecast_status = "online"
        return True
    except Exception:
        forecast_ok = False
        forecast_status = "request failed"
        return False


def ask_cloud_assistant():
    global answer_ready, last_answer, last_speech
    try:
        answer_ready = True
        last_answer = "Asking cloud..."
        last_speech = ""
        render_assistant_page()
        question = QUESTIONS[selected_question][2]
        url = (
            DEVICE_SUMMARY_URL
            + "?device_id="
            + DEVICE_ID
            + "&hours=24&question="
            + url_encode(question)
        )
        response = urequests.get(url)
        data = response.json()
        response.close()
        last_answer = fit_answer(data.get("answer", "No answer returned."))
        last_speech = fit_answer(data.get("speech", last_answer), 80)
    except Exception:
        last_answer = "Assistant request failed."
        last_speech = ""
    render_assistant_page()


def play_last_answer():
    global last_answer
    if not answer_ready or not last_answer:
        last_answer = "Ask a question first."
        render_assistant_page()
        return

    speech_text = last_speech or last_answer
    if len(speech_text) > 80:
        speech_text = speech_text[:77] + "..."

    try:
        set_lines("TTS: requesting...", "", "", "", "")
        url = DEVICE_TTS_URL + "?text=" + url_encode(speech_text)
        response = urequests.get(url)
        if response.status_code < 200 or response.status_code >= 300:
            status_code = response.status_code
            response.close()
            last_answer = "TTS HTTP " + str(status_code)
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
    current_page = (current_page + 1) % 3
    render_page()


def on_button_b():
    global answer_ready, last_answer, last_speech, selected_question
    if current_page == PAGE_ASSISTANT:
        selected_question = (selected_question + 1) % len(QUESTIONS)
        answer_ready = False
        last_answer = "Select a question."
        last_speech = ""
        render_assistant_page()


def on_button_c():
    global pending_action
    if current_page == PAGE_ASSISTANT:
        pending_action = "speak" if answer_ready else "ask"


def register_buttons():
    try:
        btnA.wasPressed(on_button_a)
        btnB.wasPressed(on_button_b)
        btnC.wasPressed(on_button_c)
    except Exception:
        pass


def main_loop():
    global latest_temp, latest_hum, latest_motion, latest_co2, last_send_ok, last_send_ms, last_weather_ms, last_render_ms, pending_action

    render_page()
    connect_wifi()
    fetch_outdoor_weather()
    fetch_forecast()
    last_weather_ms = time.ticks_ms()
    env3_sensor = init_env3() if SENSOR_MODE == "env3" else None
    co2_sensor = init_co2() if SENSOR_MODE == "co2" else None
    pir_sensor = init_pir()
    register_buttons()

    while True:
        latest_temp, latest_hum, latest_motion, latest_co2 = read_sensors(env3_sensor, pir_sensor, co2_sensor)

        now_ms = time.ticks_ms()
        if time.ticks_diff(now_ms, last_weather_ms) >= WEATHER_REFRESH_SECONDS * 1000:
            fetch_outdoor_weather()
            fetch_forecast()
            last_weather_ms = now_ms

        if time.ticks_diff(now_ms, last_send_ms) >= SEND_INTERVAL_SECONDS * 1000:
            ok = send_data_to_api(latest_temp, latest_hum, latest_motion, latest_co2)
            last_send_ok = ok
            last_send_ms = now_ms

        if pending_action == "ask":
            pending_action = None
            ask_cloud_assistant()
        elif pending_action == "speak":
            pending_action = None
            play_last_answer()

        if current_page != PAGE_ASSISTANT and time.ticks_diff(now_ms, last_render_ms) >= DATA_RENDER_SECONDS * 1000:
            render_page()
            last_render_ms = now_ms

        time.sleep(0.5)


main_loop()
