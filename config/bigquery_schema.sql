-- Schema des tables BigQuery.
--
-- Table sensor_readings :
--   id, device_id, timestamp, temperature_c, humidity_pct,
--   air_quality_index, air_quality_label, motion_detected
--
-- Table weather_history :
--   id, timestamp, city, temperature_c, feels_like_c, humidity_pct,
--   pressure_hpa, wind_speed_ms, weather_main, weather_description, weather_icon
CREATE TABLE IF NOT EXISTS `weather-station-494408.weather_station.sensor_readings` (
    id STRING NOT NULL,
    device_id STRING NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    temperature_c FLOAT64,
    humidity_pct FLOAT64,
    air_quality_index INT64,
    air_quality_label STRING,
    motion_detected BOOL
);

CREATE TABLE IF NOT EXISTS `weather-station-494408.weather_station.weather_history` (
    id STRING NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    city STRING,
    temperature_c FLOAT64,
    feels_like_c FLOAT64,
    humidity_pct FLOAT64,
    pressure_hpa FLOAT64,
    wind_speed_ms FLOAT64,
    wind_deg INT64,
    weather_main STRING,
    weather_description STRING,
    weather_icon STRING
);