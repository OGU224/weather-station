"""Routes meteo — /api/weather/
- GET /current  : meteo actuelle via OpenWeatherMap (+ stockage BQ si ?store=true)
- GET /forecast : previsions 5 jours (?days=5) — PAS stocke dans BQ
- GET /history  : historique meteo depuis BigQuery (?hours=24)
"""
