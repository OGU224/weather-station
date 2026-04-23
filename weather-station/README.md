# 🌤️ Weather Station — Cloud & Advanced Analytics

Indoor/outdoor weather monitor using M5Stack Core2, Google Cloud, and Streamlit.

## Team
| Name | Role |
|------|------|
| TODO | Device UI, sensors, alerts |
| TODO | Cloud backend, Streamlit dashboard |

## Architecture

```
UI Layer        →  M5Stack Core2 (device)  +  Streamlit (cloud dashboard)
Middleware      →  Flask API
Data Layer      →  Google BigQuery
External APIs   →  OpenWeatherMap, Google TTS/STT, OpenAI/Gemini
```

## Setup
```bash
cp .env.example .env        # Remplir avec vos clés
pip install -r requirements.txt
python -m middleware.app     # Lancer l'API
streamlit run dashboard/app.py  # Lancer le dashboard
```

## Project Structure
```
config/          → Settings .env, schéma BigQuery
data/            → Client BigQuery, modèles de données
services/        → Logique métier (météo, capteurs, alertes, voix)
middleware/      → API Flask (routes sensors, weather, voice)
device/          → Code M5Stack (main loop, WiFi, sync, UI)
dashboard/       → Streamlit (pages temps réel + historique)
```

## Video
🎥 [YouTube — TODO]
