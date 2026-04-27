from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class IndoorSensorData:
    timestamp: datetime
    device_id: str
    temperature_c: Optional[float] = None
    humidity_percent: Optional[float] = None
    co2_ppm: Optional[int] = None
    tvoc_ppb: Optional[int] = None
    motion_detected: Optional[bool] = None

    def to_dict(self):
        return {
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "device_id": self.device_id,
            "temperature_c": self.temperature_c,
            "humidity_percent": self.humidity_percent,
            "co2_ppm": self.co2_ppm,
            "tvoc_ppb": self.tvoc_ppb,
            "motion_detected": self.motion_detected
        }

@dataclass
class OutdoorWeatherData:
    timestamp: datetime
    location_name: str
    outdoor_temp_c: Optional[float] = None
    humidity_percent: Optional[float] = None
    weather_condition: Optional[str] = None
    weather_icon: Optional[str] = None

    def to_dict(self):
        return {
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "location_name": self.location_name,
            "outdoor_temp_c": self.outdoor_temp_c,
            "humidity_percent": self.humidity_percent,
            "weather_condition": self.weather_condition,
            "weather_icon": self.weather_icon
        }

@dataclass
class ForecastDay:
    date: str
    temp_min_c: float
    temp_max_c: float
    icon: str
