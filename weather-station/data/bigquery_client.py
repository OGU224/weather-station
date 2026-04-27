"""Client BigQuery.
- insert_indoor_sensor_data(reading) : stocke une lecture capteur
- insert_outdoor_weather_data(weather) : stocke une donnee meteo
- get_latest_indoor_sensor_data(device_id) : derniere lecture (pour sync au boot)
- get_indoor_sensor_history(device_id, hours) : historique capteurs
- get_outdoor_weather_history(hours) : historique meteo
"""
