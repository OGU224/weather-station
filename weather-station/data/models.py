"""Modeles de donnees (dataclasses).
- SensorReading : lecture indoor (temp, humidite, air quality, motion)
- WeatherData : meteo outdoor (temp, vent, pression, description, icone)
- ForecastDay : prevision pour un jour (date, temp min/max, icone)
Chaque modele a une methode to_dict() pour insertion BigQuery.
"""
