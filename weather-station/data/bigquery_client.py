"""Client BigQuery.
- insert_sensor_reading(reading) : stocke une lecture capteur
- insert_weather_data(weather) : stocke une donnee meteo
- get_latest_sensor_reading(device_id) : derniere lecture (pour sync au boot)
- get_sensor_history(device_id, hours) : historique capteurs
- get_weather_history(hours) : historique meteo
"""
