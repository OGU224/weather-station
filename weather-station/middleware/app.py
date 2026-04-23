"""Flask app principale.
- Factory create_app() qui enregistre les blueprints
- Route /api/health pour verifier que le serveur tourne
- CORS active pour les requetes du M5Stack et Streamlit
- Blueprints : sensor_bp (/api/sensors), weather_bp (/api/weather), voice_bp (/api/voice)
"""
