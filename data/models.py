"""Dataclasses shared by the middleware, BigQuery client, and services."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
import uuid
from typing import Optional


# Represent one indoor reading sent by a Core2 device.
@dataclass
class SensorReading:
    motion_detected: bool = False
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    air_quality_index: Optional[int] = None
    device_id: str = "m5stack-01"
    air_quality_label: str = ""
    co2_source: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Fill the air-quality label automatically from the CO2 value.
    def __post_init__(self):
        if self.air_quality_index is None:
            self.air_quality_label = self.air_quality_label or "not measured"
        elif not self.air_quality_label:
            if self.air_quality_index < 800:
                self.air_quality_label = "good"
            elif self.air_quality_index < 1200:
                self.air_quality_label = "moderate"
            else:
                self.air_quality_label = "bad"

    # Convert the sensor reading into a BigQuery-friendly dictionary.
    def to_dict(self):
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d


# Represent one current outdoor weather snapshot.
@dataclass
class WeatherData:
    temperature_c: float
    feels_like_c: float
    humidity_pct: float
    pressure_hpa: float
    wind_speed_ms: float
    wind_deg: int
    weather_main: str
    weather_description: str
    weather_icon: str
    city: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Convert the weather snapshot into a BigQuery-friendly dictionary.
    def to_dict(self):
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d


# Represent one daily forecast summary.
@dataclass
class ForecastDay:
    date: str
    temp_min: float
    temp_max: float
    weather_main: str
    weather_description: str
    weather_icon: str
