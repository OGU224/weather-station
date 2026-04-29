"""
Modèles de données.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
import uuid


@dataclass
class SensorReading:
    temperature_c: float
    humidity_pct: float
    air_quality_index: int
    motion_detected: bool
    device_id: str = "m5stack-01"
    air_quality_label: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self):
        if not self.air_quality_label:
            if self.air_quality_index < 50:
                self.air_quality_label = "good"
            elif self.air_quality_index < 100:
                self.air_quality_label = "moderate"
            else:
                self.air_quality_label = "bad"

    def to_dict(self):
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d


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

    def to_dict(self):
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d


@dataclass
class ForecastDay:
    date: str
    temp_min: float
    temp_max: float
    weather_main: str
    weather_description: str
    weather_icon: str
