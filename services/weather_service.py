"""Service meteo — OpenWeatherMap.
- get_current_weather() -> WeatherData
- get_forecast(days=5) -> list[ForecastDay]
- get_icon_url(icon_code) -> URL de l icone
Utilise OWM_API_KEY et OWM_CITY depuis config.
"""
"""
Service météo — OpenWeatherMap.
"""

import logging
import requests

from config import OWM_API_KEY, OWM_BASE_URL, OWM_CITY, OWM_COUNTRY_CODE, OWM_UNITS, OWM_LANG
from data.models import WeatherData, ForecastDay

logger = logging.getLogger(__name__)


class WeatherService:

    def __init__(self):
        self.last_error = None
        self.default_params = {
            "q": f"{OWM_CITY},{OWM_COUNTRY_CODE}",
            "units": OWM_UNITS,
            "lang": OWM_LANG,
            "appid": OWM_API_KEY,
        }

    def _params(self, city=None, country_code=None, lat=None, lon=None):
        params = dict(self.default_params)
        if lat is not None and lon is not None:
            params.pop("q", None)
            params["lat"] = lat
            params["lon"] = lon
        elif city:
            suffix = ""
            if country_code:
                suffix = "," + str(country_code)
            params["q"] = str(city) + suffix
        return params

    def get_current_weather(self, city=None, country_code=None, lat=None, lon=None):
        try:
            self.last_error = None
            params = self._params(city=city, country_code=country_code, lat=lat, lon=lon)
            resp = requests.get(f"{OWM_BASE_URL}/weather", params=params, timeout=10)
            resp.raise_for_status()
            d = resp.json()
            return WeatherData(
                temperature_c=d["main"]["temp"],
                feels_like_c=d["main"]["feels_like"],
                humidity_pct=d["main"]["humidity"],
                pressure_hpa=d["main"]["pressure"],
                wind_speed_ms=d["wind"]["speed"],
                wind_deg=d["wind"].get("deg", 0),
                weather_main=d["weather"][0]["main"],
                weather_description=d["weather"][0]["description"],
                weather_icon=d["weather"][0]["icon"],
                city=d["name"],
            )
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Erreur OpenWeatherMap: {e}")
            return None

    def get_forecast(self, days=5, city=None, country_code=None, lat=None, lon=None):
        try:
            self.last_error = None
            params = self._params(city=city, country_code=country_code, lat=lat, lon=lon)
            resp = requests.get(f"{OWM_BASE_URL}/forecast", params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            daily = {}
            for item in data["list"]:
                date_str = item["dt_txt"].split(" ")[0]
                daily.setdefault(date_str, []).append(item)

            forecasts = []
            for date_str, items in list(daily.items())[:days]:
                temps = [i["main"]["temp"] for i in items]
                mains = [i["weather"][0]["main"] for i in items]
                most_common = max(set(mains), key=mains.count)
                rep = next(i for i in items if i["weather"][0]["main"] == most_common)
                forecasts.append(ForecastDay(
                    date=date_str,
                    temp_min=round(min(temps), 1),
                    temp_max=round(max(temps), 1),
                    weather_main=most_common,
                    weather_description=rep["weather"][0]["description"],
                    weather_icon=rep["weather"][0]["icon"],
                ))
            return forecasts
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Erreur forecast: {e}")
            return []
