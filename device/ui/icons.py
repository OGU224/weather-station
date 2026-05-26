"""Icones meteo pixel-art pour M5Stack Core2."""

try:
    from M5 import Lcd
except ImportError:
    Lcd = None

IPX = 3
YELLOW = 0xFFFF00
WHITE = 0xFFFFFF
GRAY = 0xAAAAAA
DARK = 0x666666
CYAN = 0x00DDFF
BLUE = 0x3388FF

_ICON_SUN = ["....Y...",".Y..Y..Y","..YYYY..",".YYYYYY.",".YYYYYY.","..YYYY..",".Y..Y..Y","....Y..."]
_ICON_CLOUD = ["........","..WWWW..",".WWWWWW.",".WWWWWW.","WWWWWWWW","WWWWWWWW","........","........"]
_ICON_RAIN = ["..WWWW..",".WWWWWW.","WWWWWWWW","WWWWWWWW","........",".C..C..C","..C..C..","........"]
_ICON_THUNDER = ["..WWWW..",".WWWWWW.","WWWWWWWW","...YY...","..YY....","..YYYY..","....YY..","........"]
_ICON_SNOW = ["..WWWW..",".WWWWWW.","WWWWWWWW","........",".W..W..W","..W..W..",".W..W..W","........"]
_ICON_MIST = ["........","WWWWWWWW","........",".WWWWWW.","........","WWWWWWWW","........",".WWWWWW."]
_ICON_PARTLY = ["....Y...","..YYYY..",".YYYYYY.","..YWWWW.","WWWWWWWW","WWWWWWWW","........","........"]
_ICON_DRIZZLE = ["..WWWW..",".WWWWWW.","WWWWWWWW","........","..C...C.","........",".C...C..","........"]

_IPAL = {".": None, "Y": YELLOW, "W": WHITE, "C": CYAN, "G": GRAY, "D": DARK, "B": BLUE}


def _draw_icon_sprite(sprite, x, y, px=IPX):
    if not Lcd:
        return
    for r, row in enumerate(sprite):
        for c, ch in enumerate(row):
            color = _IPAL.get(ch)
            if color is not None:
                Lcd.fillRect(x + c * px, y + r * px, px, px, color)


_OWM_MAP = {"01": _ICON_SUN, "02": _ICON_PARTLY, "03": _ICON_CLOUD, "04": _ICON_CLOUD, "09": _ICON_DRIZZLE, "10": _ICON_RAIN, "11": _ICON_THUNDER, "13": _ICON_SNOW, "50": _ICON_MIST}
_NAME_MAP = {"clear": _ICON_SUN, "clouds": _ICON_CLOUD, "rain": _ICON_RAIN, "drizzle": _ICON_DRIZZLE, "thunderstorm": _ICON_THUNDER, "snow": _ICON_SNOW, "mist": _ICON_MIST, "fog": _ICON_MIST, "haze": _ICON_MIST}


def draw_weather_icon(icon_code="", weather_main="", x=0, y=0, px=IPX):
    sprite = None
    if icon_code and len(icon_code) >= 2:
        sprite = _OWM_MAP.get(icon_code[:2])
    if not sprite and weather_main:
        name = str(weather_main).lower()
        for key, spr in _NAME_MAP.items():
            if key in name:
                sprite = spr
                break
    if not sprite:
        sprite = _ICON_CLOUD
    _draw_icon_sprite(sprite, x, y, px)


def get_weather_symbol(weather_main=""):
    name = str(weather_main).lower()
    if "clear" in name or "sun" in name: return "*"
    if "cloud" in name: return "~"
    if "rain" in name or "drizzle" in name: return ";"
    if "thunder" in name: return "!"
    if "snow" in name: return "+"
    if "mist" in name or "fog" in name: return "="
    return "?"


def draw_forecast_icon(weather_main, x, y):
    draw_weather_icon(weather_main=weather_main, x=x, y=y, px=2)
