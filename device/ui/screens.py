"""Ecrans M5Stack style Undertale (320x240 pixels)."""

try:
    from M5 import Lcd
except ImportError:
    Lcd = None

from companion import Buddy, CHARACTERS, draw_sprite, PX
from components import (
    clear_screen, draw_topbar, draw_dialogue_box, draw_dialogue_text,
    draw_hp_bar, draw_menu, draw_heart_cursor, _clean,
    BLACK, WHITE, YELLOW, RED, CYAN, GREEN, GRAY, HEART_RED, ORANGE, FONT_SM,
    hide_all_components
)
from icons import draw_weather_icon

PAGE_DATA = 0
PAGE_FORECAST = 1
PAGE_ASSISTANT = 2
PAGE_TREND = 3
PAGE_WIFI = 4
PAGE_CHARACTER = 5
PAGE_COUNT = 6


def _safe_float(value, default=0):
    try:
        return float(value)
    except:
        return default


def _short(text, max_chars):
    value = _clean(str(text or ""))
    if len(value) <= max_chars:
        return value
    return value[:max_chars - 3].rstrip(" ,.;:") + "..."


def _draw_lines(text, x, y, chars=28, max_lines=3, color=WHITE, bg=BLACK, bullet=False):
    if not Lcd:
        return
    words = _clean(str(text or "")).split(" ")
    lines = []
    current = "* " if bullet else ""
    for word in words:
        if not word:
            continue
        candidate = word if current == "" else current + " " + word
        if len(candidate) <= chars:
            current = candidate
        elif len(lines) < max_lines:
            lines.append(current)
            current = ("* " if bullet else "") + word
        else:
            break
    if current and len(lines) < max_lines:
        lines.append(current)

    if FONT_SM:
        Lcd.setFont(FONT_SM)
    for i in range(max_lines):
        Lcd.fillRect(x, y + i * 17, chars * 8, 17, bg)
        if i < len(lines):
            Lcd.setTextColor(color, bg)
            Lcd.drawString(lines[i], x, y + i * 17)


def _draw_status_chip(text, x, y, color):
    if not Lcd:
        return
    Lcd.fillRect(x, y, 92, 20, 0x111111)
    Lcd.drawRect(x, y, 92, 20, color)
    if FONT_SM:
        Lcd.setFont(FONT_SM)
    Lcd.setTextColor(color, 0x111111)
    Lcd.drawString(_short(text, 10), x + 6, y + 3)


def _draw_footer(selected, hint="A page   B next   C action"):
    if not Lcd:
        return
    Lcd.fillRect(0, 214, 320, 26, BLACK)
    if FONT_SM:
        Lcd.setFont(FONT_SM)
    start_x = 124
    for i in range(4):
        color = HEART_RED if i == selected else 0x444444
        Lcd.fillRect(start_x + i * 18, 219, 7, 7, color)
    Lcd.setTextColor(GRAY, BLACK)
    Lcd.drawString(_short(hint, 28), 70, 228)


def _clock_label(state, fallback=""):
    time_text = str(state.get("tstr", "") or "")
    date_text = str(state.get("dstr", "") or "")
    if time_text and time_text != "--:--":
        if date_text and date_text != "--/--":
            return "{} {}".format(date_text, time_text)
        return time_text
    return fallback


def _render_busy(title, message, buddy):
    hide_all_components()
    clear_screen()
    draw_topbar("* " + title, "", bg=BLACK)
    buddy.set_state(Buddy.SPEAK)
    buddy.reset_motion_cache()
    buddy.draw(cx=160, cy=72, bg=BLACK)
    draw_dialogue_box(28, 126, 264, 56)
    _draw_lines(message, x=42, y=140, chars=24, max_lines=2, color=YELLOW, bullet=True)


def render_busy_screen(title, message, buddy):
    _render_busy(title, message, buddy)


# ============================================================
#  PAGE DATA
# ============================================================

def render_data(state, buddy, full=False):
    if full:
        hide_all_components()
        clear_screen()
        buddy.reset_motion_cache()

    draw_topbar("* WEATHER", _clock_label(state, "LV {}".format(_comfort_level(state))))

    _update_buddy_state(buddy, state)
    buddy.draw(cx=160, cy=55, bg=BLACK)

    if full:
        draw_dialogue_box(12, 92, 296, 72)

    _draw_lines(_build_status_message(state), x=22, y=101, chars=27, max_lines=3, bullet=True)

    if state.get("sensor_mode") == "co2":
        co2 = state.get("co2") or 400
        air_score = 100 - max(0, min(100, int((co2 - 400) / 12)))
        draw_hp_bar(air_score, x=16, y=176, w=150)
    else:
        hum = state.get("hum") or 0
        draw_hp_bar(hum, x=16, y=176, w=150)

    icon, main = state.get("o_icon", ""), state.get("o_main", "")
    draw_weather_icon(icon_code=icon, weather_main=main, x=270, y=174, px=3)
    _draw_footer(PAGE_DATA, "A page   B refresh")


def _comfort_level(state):
    score = 10
    hum, temp = state.get("hum"), state.get("temp")
    if hum is not None:
        if 40 <= hum <= 60: score += 5
        elif hum < 30 or hum > 70: score -= 3
    if temp is not None:
        if 19 <= temp <= 24: score += 5
        elif temp < 16 or temp > 28: score -= 3
    return max(1, min(20, score))


def _update_buddy_state(buddy, state):
    hum, temp = state.get("hum"), state.get("temp")
    if hum is not None and hum < 40: return buddy.set_state(Buddy.ALERT)
    if hum is not None and 40 <= hum <= 60 and temp is not None and 19 <= temp <= 24:
        return buddy.set_state(Buddy.HAPPY)
    buddy.set_state(Buddy.IDLE)


def _build_status_message(state):
    hum, temp = state.get("hum"), state.get("temp")
    co2 = state.get("co2")
    o_temp, o_main = state.get("o_temp", "--"), state.get("o_main", "")
    if state.get("sensor_mode") == "co2":
        if co2 is not None:
            if co2 >= 1200: return "Air quality alert. CO2 {} ppm. Open a window.".format(co2)
            if co2 >= 900: return "CO2 {} ppm. Room air is getting heavy.".format(co2)
            return "CO2 {} ppm. Air quality looks good.".format(co2)
        return "Waiting for CO2 sensor..."
    if hum is not None and hum < 40: return "Dry room. Indoor {}C / {}%. Add humidity.".format(temp, int(hum))
    if hum is not None and hum > 70: return "Humid room. Indoor {}C / {}%. Ventilate.".format(temp, int(hum))
    if temp is not None and hum is not None and state.get("o_ok"):
        return "Indoor {}C / {}%. Outside {}C, {}.".format(temp, int(hum), o_temp, o_main)
    if temp is not None and hum is not None:
        return "Indoor {}C / {}%. Outdoor loading.".format(temp, int(hum))
    return "Waiting for sensor data..."


# ============================================================
#  PAGE FORECAST
# ============================================================

def render_forecast(state, buddy, full=False):
    fcast = state.get("fcast", [])
    if full:
        hide_all_components()
        clear_screen()
        draw_topbar("* FORECAST", _clock_label(state, "{} days".format(len(fcast))), bg=BLACK)
        _draw_footer(PAGE_FORECAST, "A page   B refresh")
        buddy.reset_motion_cache()
        for i in range(min(3, len(fcast))):
            fy = 62 + i * 43
            if Lcd:
                Lcd.fillRect(10, fy, 300, 36, 0x111111 if i % 2 == 0 else BLACK)
                Lcd.drawRect(10, fy, 300, 36, 0x333333)
        if not fcast:
            draw_dialogue_box(20, 80, 280, 50)

    buddy.draw_small(cx=36, cy=42, bg=BLACK)

    rain_day = False
    for f in fcast:
        if "rain" in str(f.get("weather_main", "")).lower():
            rain_day = True
            break
    
    if Lcd:
        if FONT_SM: Lcd.setFont(FONT_SM)
        Lcd.setTextColor(CYAN if rain_day else GRAY, BLACK)
        Lcd.drawString("* Umbrella soon!" if rain_day else "* Looking good ahead!", 76, 32)

    for i in range(min(3, len(fcast))):
        fc = fcast[i]
        fy = 62 + i * 43
        date = str(fc.get("date", ""))
        if len(date) >= 10: date = date[5:10]
        t_max = round(_safe_float(fc.get("temp_max", 0)), 1)
        t_min = round(_safe_float(fc.get("temp_min", 0)), 1)
        main, icon = str(fc.get("weather_main", "")), str(fc.get("weather_icon", ""))

        draw_weather_icon(icon_code=icon, weather_main=main, x=18, y=fy + 6, px=2)
        
        if Lcd:
            Lcd.setTextColor(CYAN if "rain" in main.lower() else WHITE, 0x111111 if i % 2 == 0 else BLACK)
            line = "{}  {}  {}-{}C".format(date, _short(main, 8), t_min, t_max)
            Lcd.drawString(_clean(line), 52, fy + 10)

    if not fcast:
        draw_dialogue_text("No forecast data yet.", x=30, y=90)


# ============================================================
#  PAGE ASSISTANT
# ============================================================

QUESTIONS = [
    ("Rain", "Rain this week?", "Will it rain in the forecast period? Max 18 words."),
    ("Outfit", "What should I wear?", "Give clothing advice for today. Max 18 words."),
    ("Room", "Is my room healthy?", "Check indoor comfort and air quality. Max 18 words."),
    ("Ventilate", "Open the window?", "Should I open the window now? Max 18 words."),
    ("Voice", "Speak to me", "VOICE_RECORD"),
]

def render_assistant(state, buddy, full=False):
    qi, ans_ok = state.get("qi", 0), state.get("ans_ok", False)
    ans_txt = state.get("ans_txt", "Select a question.")

    if full:
        hide_all_components()
        clear_screen()
        draw_topbar("* ASSISTANT", _clock_label(state, "Gemini"), bg=BLACK)
        _draw_footer(PAGE_ASSISTANT, "A page   B next   C ask")
        buddy.reset_motion_cache()

    busy = ans_txt not in ("Select a question.", "") and not ans_ok
    busy_text = str(ans_txt or "").lower()
    if busy:
        if "speak now" in busy_text:
            _render_busy("LISTEN", "Speak now", buddy)
            return
        if "transcribing" in busy_text:
            _render_busy("TRANSCRIBE", "Understanding voice", buddy)
            return
        if "speaking" in busy_text:
            _render_busy("SPEAKING", "Playing answer", buddy)
            return
        if "thinking" in busy_text or "preparing" in busy_text:
            _render_busy("THINKING", "Asking assistant", buddy)
            return

    if ans_ok or busy:
        buddy.set_state(Buddy.SPEAK)
    else:
        buddy.set_state(Buddy.IDLE)

    buddy.draw_small(cx=42, cy=42, bg=BLACK)

    if ans_ok:
        if Lcd:
            Lcd.fillRect(8, 58, 304, 122, BLACK)
            draw_dialogue_box(10, 62, 300, 94)
        _draw_lines(ans_txt, x=22, y=73, chars=27, max_lines=4, bullet=True)
        if Lcd:
            Lcd.setTextColor(YELLOW, BLACK)
            Lcd.drawString("B next question", 34, 166)
            Lcd.drawString("C speak answer", 178, 166)
        _draw_footer(PAGE_ASSISTANT, "A page   B next   C speak")
    elif busy:
        if Lcd:
            Lcd.fillRect(8, 58, 304, 132, BLACK)
            draw_dialogue_box(28, 86, 264, 68)
        _draw_lines(ans_txt, x=42, y=100, chars=24, max_lines=2, color=YELLOW, bullet=True)
    else:
        name, desc, prompt = QUESTIONS[qi]
        if Lcd:
            Lcd.fillRect(8, 58, 304, 132, BLACK)
            Lcd.setTextColor(GRAY, BLACK)
            Lcd.drawString("Selected question", 70, 56)
            _draw_status_chip(str(qi + 1) + "/5", 220, 52, YELLOW)
            draw_dialogue_box(16, 82, 288, 72)
            Lcd.setTextColor(YELLOW, BLACK)
            Lcd.drawString(_clean(name), 30, 94)
        _draw_lines(desc, x=30, y=116, chars=25, max_lines=2, color=WHITE)
        is_voice = QUESTIONS[qi][2] == "VOICE_RECORD"
        if Lcd:
            Lcd.setTextColor(GRAY, BLACK)
            Lcd.drawString("B change", 46, 176)
            Lcd.drawString("C record" if is_voice else "C ask", 184, 176)
        _draw_footer(PAGE_ASSISTANT, "A page   B change   C ask")


# ============================================================
#  PAGE TREND
# ============================================================

def render_trend(state, buddy, full=False):
    if full:
        hide_all_components()
        clear_screen()
        draw_topbar("* TREND", _clock_label(state, "24h"), bg=BLACK)
        buddy.reset_motion_cache()
        draw_dialogue_box(12, 54, 296, 118)

    buddy.draw_small(cx=44, cy=36, bg=BLACK)

    temp_avg = state.get("trend_temp", "--")
    hum_avg = state.get("trend_hum", "--")
    motion_count = state.get("trend_motion", "--")
    co2_value = state.get("trend_co2", "--")
    sync = state.get("sync_status", "")

    _draw_lines(
        "Last 24h: temp {}C, humidity {}%.".format(temp_avg, hum_avg),
        x=26,
        y=68,
        chars=26,
        max_lines=2,
        bullet=True,
    )
    _draw_lines(
        "Motion events: {}. CO2: {}.".format(motion_count, co2_value),
        x=26,
        y=105,
        chars=26,
        max_lines=2,
        color=CYAN,
        bullet=True,
    )
    _draw_lines(
        sync or "Boot sync ready.",
        x=26,
        y=142,
        chars=26,
        max_lines=1,
        color=YELLOW,
        bullet=True,
    )
    _draw_footer(PAGE_TREND, "A page   B refresh")


# ============================================================
#  PAGE WIFI
# ============================================================

def render_wifi(state, full=False):
    if full:
        hide_all_components()
        clear_screen()
        draw_topbar("* WIFI SETUP", _clock_label(state, ""), bg=BLACK)
        _draw_footer(PAGE_WIFI, "B choose   C connect")
        if Lcd: Lcd.fillRect(10, 30, 300, 140, BLACK)
        state_status = state.get("wifi_status", "")
        if state_status:
            draw_dialogue_box(8, 150, 304, 40)

    profiles, idx, status = state.get("wifi_profiles", []), state.get("wifi_idx", 0), state.get("wifi_status", "")

    if Lcd and FONT_SM: Lcd.setFont(FONT_SM)
    for i, prof in enumerate(profiles[:5]):
        wy = 30 + i * 28
        color = YELLOW if i == idx else GRAY
        if i == idx and Lcd:
            Lcd.fillRect(10, wy, 16, 24, BLACK)
            draw_heart_cursor(14, wy + 6)
        
        if Lcd:
            Lcd.setTextColor(color, BLACK)
            line = "{} ({})".format(prof.get("name", prof.get("ssid", "?")), prof.get("ssid", ""))
            Lcd.drawString(_clean(line), 30, wy + 4)

    if status:
        draw_dialogue_text(status, x=16, y=156, max_lines=2)

    if Lcd:
        Lcd.setTextColor(GRAY, BLACK)
        Lcd.drawString("B:next network  C:connect", 20, 200)
    _draw_footer(PAGE_WIFI, "B choose   C connect")


# ============================================================
#  PAGE CHARACTER
# ============================================================

def render_character_select(buddy, char_idx, full=False):
    if full:
        hide_all_components()
        clear_screen()
        draw_topbar("* CHOOSE YOUR COMPANION", "", bg=BLACK)
        draw_dialogue_box(8, 182, 304, 34)
        buddy.reset_motion_cache()
        if Lcd: Lcd.fillRect(128, 24, 16 * PX, 16 * PX, BLACK)

    char = CHARACTERS[char_idx]
    draw_sprite(char["sprites"]["idle"], 128, 24, bg_color=BLACK, px=PX)

    if Lcd:
        if FONT_SM: Lcd.setFont(FONT_SM)
        Lcd.setTextColor(YELLOW, BLACK)
        Lcd.drawString(_clean(char["name"]), 100, 96)

    mini_y, mini_px, slot_w = 130, 2, 320 // 6
    for i, ch in enumerate(CHARACTERS):
        mx = i * slot_w + (slot_w - 16 * mini_px) // 2
        bg = 0x222222 if i == char_idx else BLACK
        if full and Lcd:
            Lcd.fillRect(mx - 2, mini_y - 2, 16 * mini_px + 4, 16 * mini_px + 4, bg)
            if i == char_idx: Lcd.drawRect(mx - 2, mini_y - 2, 16 * mini_px + 4, 16 * mini_px + 4, YELLOW)
        draw_sprite(ch["sprites"]["idle"], mx, mini_y, bg_color=bg, px=mini_px)

    if Lcd: 
        if full: Lcd.fillRect(0, mini_y + 16 * mini_px + 4, 320, 8, BLACK)
        draw_heart_cursor(char_idx * slot_w + slot_w // 2 - 3, mini_y + 16 * mini_px + 4)
        
    draw_dialogue_text("B:browse  C:select  A:back", x=16, y=188, max_lines=1)


# ============================================================
#  DISPATCHER
# ============================================================

def render(page, state, buddy, full=True):
    if page == PAGE_DATA: render_data(state, buddy, full)
    elif page == PAGE_FORECAST: render_forecast(state, buddy, full)
    elif page == PAGE_ASSISTANT: render_assistant(state, buddy, full)
    elif page == PAGE_TREND: render_trend(state, buddy, full)
    elif page == PAGE_WIFI: render_wifi(state, full)
    elif page == PAGE_CHARACTER: render_character_select(buddy, state.get("char_idx", buddy.char_idx), full)
