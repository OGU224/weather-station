"""Routes capteurs — /api/sensors/
- POST /reading : recoit {temperature_c, humidity_pct, air_quality_index, motion_detected}
                  -> stocke dans BigQuery, retourne alertes eventuelles
- GET  /latest  : derniere lecture (sync au demarrage du device)
- GET  /history : historique sur N heures (?hours=24)
"""
