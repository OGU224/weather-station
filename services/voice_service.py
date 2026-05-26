"""Voice and assistant service."""

import os
import base64
import re
from io import BytesIO
from datetime import datetime, timezone
import wave
import subprocess
import tempfile

from dotenv import load_dotenv

from data.bigquery_client import BigQueryClient
from services.device_location_service import get_device_location
from services.geolocation_service import get_ip_location
from services.weather_service import WeatherService

load_dotenv(override=True)

DEFAULT_TTS_LANGUAGE = os.getenv("GOOGLE_TTS_LANGUAGE", "en-US")
DEFAULT_TTS_VOICE = os.getenv("GOOGLE_TTS_VOICE", "en-US-Standard-F")
DEFAULT_STT_LANGUAGE = os.getenv("GOOGLE_STT_LANGUAGE", "en-US")
DEFAULT_STT_ALT_LANGUAGES = [
    item.strip()
    for item in os.getenv("GOOGLE_STT_ALT_LANGUAGES", "fr-FR").split(",")
    if item.strip()
]
DEFAULT_STT_PHRASES = [
    item.strip()
    for item in os.getenv(
        "GOOGLE_STT_PHRASES",
        (
            "temperature,humidity,humid,CO2,carbon dioxide,air quality,forecast,"
            "weather,outside,indoor,outdoor,motion,presence,detected,ventilate,"
            "window,umbrella,rain,raining,yesterday,two days ago,last 24 hours,"
            "exceeded,above,below,average,Lausanne,Geneva,Geneve,meteo,humidite,temperature,"
            "qualite de l air,parapluie,pluie,fenetre"
        ),
    ).split(",")
    if item.strip()
]
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_TTS_MODEL = os.getenv("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")
GEMINI_TTS_VOICE = os.getenv("GEMINI_TTS_VOICE", "Kore")
GEMINI_TTS_GAIN = float(os.getenv("GEMINI_TTS_GAIN", "3.0"))
GOOGLE_TTS_GAIN = float(os.getenv("GOOGLE_TTS_GAIN", "2.0"))
WINDOWS_TTS_GAIN = float(os.getenv("WINDOWS_TTS_GAIN", "1.8"))
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "12"))


INTENT_KEYWORDS = {
    "rain_forecast": [
        "rain", "raining", "rainy", "umbrella", "drizzle", "storm", "wet",
        "pluie", "pleut", "pleuvoir", "parapluie", "averse", "orage",
    ],
    "outfit": [
        "wear", "clothes", "clothing", "dress", "jacket", "coat", "sunglasses",
        "sunscreen", "outfit", "put on", "bring",
        "porter", "mettre", "habiller", "veste", "manteau", "lunettes", "creme",
    ],
    "outdoor_weather": [
        "outside", "outdoor", "weather", "forecast", "temperature outside",
        "meteo", "dehors", "exterieur", "temps", "prevision", "temperature dehors",
    ],
    "ventilation": [
        "window", "ventilate", "ventilation", "air out", "open", "close",
        "fenetre", "aerer", "aeration", "ouvrir", "fermer",
    ],
    "room_health": [
        "healthy", "comfort", "comfortable", "room", "indoor", "inside", "home",
        "sain", "confort", "chambre", "piece", "interieur", "maison",
    ],
    "humidity": ["humidity", "humid", "dry", "moisture", "humidite", "humide", "sec"],
    "temperature": ["temperature", "temp", "hot", "cold", "warm", "chaud", "froid"],
    "co2": ["co2", "carbon", "air quality", "quality", "air", "ppm", "qualite"],
    "motion": ["motion", "movement", "presence", "detected", "mouvement", "presence"],
    "average": ["average", "avg", "mean", "trend", "history", "moyenne", "tendance", "historique"],
    "historical": [
        "yesterday", "today", "ago", "last", "history", "historical", "exceeded", "exceed",
        "above", "below", "higher", "lower", "over", "under",
        "hier", "aujourd hui", "avant", "dernier", "historique", "depasse", "plus", "moins",
    ],
}


def _amplify_pcm(pcm_data, gain, target_peak=28000):
    """Amplify signed 16-bit little-endian PCM without harsh clipping."""
    if gain <= 1:
        return pcm_data

    peak = 0
    for index in range(0, len(pcm_data) - 1, 2):
        sample = int.from_bytes(pcm_data[index:index + 2], "little", signed=True)
        abs_sample = abs(sample)
        if abs_sample > peak:
            peak = abs_sample

    if peak > 0:
        max_safe_gain = float(target_peak) / float(peak)
        gain = min(gain, max_safe_gain)

    amplified = bytearray(len(pcm_data))
    for index in range(0, len(pcm_data) - 1, 2):
        sample = int.from_bytes(pcm_data[index:index + 2], "little", signed=True)
        boosted = int(sample * gain)
        if boosted > 32767:
            boosted = 32767
        elif boosted < -32768:
            boosted = -32768
        amplified[index:index + 2] = boosted.to_bytes(2, "little", signed=True)
    return bytes(amplified)


def _wav_bytes_from_pcm(pcm_data, channels=1, rate=24000, sample_width=2):
    pcm_data = _amplify_pcm(pcm_data, GEMINI_TTS_GAIN)
    buffer = BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(rate)
        wav_file.writeframes(pcm_data)
    return buffer.getvalue()


def _boost_wav_bytes(wav_data, gain):
    if gain <= 1:
        return wav_data
    source = BytesIO(wav_data)
    target = BytesIO()
    with wave.open(source, "rb") as input_wav:
        params = input_wav.getparams()
        frames = input_wav.readframes(input_wav.getnframes())
    if params.sampwidth != 2:
        return wav_data
    frames = _amplify_pcm(frames, gain)
    with wave.open(target, "wb") as output_wav:
        output_wav.setparams(params)
        output_wav.writeframes(frames)
    return target.getvalue()


def _synthesize_with_gemini(text):
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return None

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=GEMINI_TTS_MODEL,
        contents=f"Say clearly and naturally: {text}",
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=GEMINI_TTS_VOICE,
                    )
                )
            ),
        ),
    )
    inline_data = response.candidates[0].content.parts[0].inline_data.data
    pcm_data = base64.b64decode(inline_data) if isinstance(inline_data, str) else inline_data
    return _wav_bytes_from_pcm(pcm_data), "audio/wav", "gemini-tts"


def _synthesize_with_google_cloud(text, language_code=None, voice_name=None):
    """Generate WAV audio through Google Cloud Text-to-Speech."""
    try:
        from google.cloud import texttospeech
    except ImportError:
        return None

    language_code = language_code or DEFAULT_TTS_LANGUAGE
    voice_name = voice_name or DEFAULT_TTS_VOICE

    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice_kwargs = {"language_code": language_code}
    if voice_name:
        voice_kwargs["name"] = voice_name
    else:
        voice_kwargs["ssml_gender"] = texttospeech.SsmlVoiceGender.NEUTRAL

    response = client.synthesize_speech(
        input=synthesis_input,
        voice=texttospeech.VoiceSelectionParams(**voice_kwargs),
        audio_config=texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            speaking_rate=float(os.getenv("GOOGLE_TTS_SPEAKING_RATE", "1.0")),
            pitch=float(os.getenv("GOOGLE_TTS_PITCH", "0.0")),
        ),
    )
    audio = _boost_wav_bytes(response.audio_content, GOOGLE_TTS_GAIN)
    return audio, "audio/wav", "google-cloud-tts"


def _powershell_quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def _synthesize_with_windows_sapi(text):
    """Generate WAV locally on Windows when Gemini TTS is unreachable."""
    if os.name != "nt":
        return None

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        wav_path = tmp.name

    script = (
        "$ErrorActionPreference = 'Stop'; "
        "$path = " + _powershell_quote(wav_path) + "; "
        "$text = " + _powershell_quote(text) + "; "
        "$voice = New-Object -ComObject SAPI.SpVoice; "
        "$stream = New-Object -ComObject SAPI.SpFileStream; "
        "$stream.Open($path, 3, $false); "
        "$voice.AudioOutputStream = $stream; "
        "$voice.Rate = 0; "
        "$voice.Volume = 100; "
        "$voice.Speak($text) | Out-Null; "
        "$stream.Close(); "
    )

    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if completed.returncode != 0:
            raise RuntimeError((completed.stderr or completed.stdout or "Windows SAPI failed").strip())
        with open(wav_path, "rb") as wav_file:
            audio = wav_file.read()
        if len(audio) <= 64:
            raise RuntimeError("Windows SAPI returned empty audio.")
        audio = _boost_wav_bytes(audio, WINDOWS_TTS_GAIN)
        return audio, "audio/wav", "windows-sapi"
    finally:
        try:
            os.remove(wav_path)
        except OSError:
            pass


def synthesize_speech(text, language_code=None, voice_name=None):
    """Return WAV audio bytes from Google Cloud TTS, with local fallbacks."""
    if not text or not text.strip():
        raise ValueError("Text is required.")

    text = text.strip()

    try:
        google_result = _synthesize_with_google_cloud(
            text=text,
            language_code=language_code,
            voice_name=voice_name,
        )
        if google_result:
            return google_result
    except Exception as exc:
        google_error = exc
    else:
        google_error = None

    try:
        gemini_result = _synthesize_with_gemini(text)
        if gemini_result:
            return gemini_result
    except Exception as exc:
        sapi_result = _synthesize_with_windows_sapi(text)
        if sapi_result:
            return sapi_result
        if google_error:
            raise RuntimeError(f"Google TTS failed: {google_error}; Gemini TTS failed: {exc}") from exc
        raise RuntimeError(f"Gemini TTS failed: {exc}") from exc

    sapi_result = _synthesize_with_windows_sapi(text)
    if sapi_result:
        return sapi_result

    raise RuntimeError("GEMINI_API_KEY is not configured and Windows TTS is unavailable.")


def transcribe_speech(audio_bytes, language_code=None, content_type=None):
    """Transcribe short audio bytes with Google Cloud Speech-to-Text."""
    if not audio_bytes:
        raise ValueError("Audio is required.")

    try:
        from google.cloud import speech
    except ImportError as exc:
        raise RuntimeError("google-cloud-speech is not installed.") from exc

    language_code = language_code or DEFAULT_STT_LANGUAGE
    client = speech.SpeechClient()
    content_type = (content_type or "").lower()

    encoding = speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED
    sample_rate_hertz = None
    if "webm" in content_type or "opus" in content_type:
        encoding = speech.RecognitionConfig.AudioEncoding.WEBM_OPUS
    elif "l16" in content_type or "pcm" in content_type or "octet-stream" in content_type:
        encoding = speech.RecognitionConfig.AudioEncoding.LINEAR16
        sample_rate_hertz = int(os.getenv("GOOGLE_STT_RAW_SAMPLE_RATE", "8000"))
    elif "wav" in content_type or "wave" in content_type:
        encoding = speech.RecognitionConfig.AudioEncoding.LINEAR16
        try:
            with wave.open(BytesIO(audio_bytes), "rb") as wav_file:
                sample_rate_hertz = wav_file.getframerate()
        except wave.Error:
            sample_rate_hertz = None
    elif "flac" in content_type:
        encoding = speech.RecognitionConfig.AudioEncoding.FLAC

    config_kwargs = {
        "language_code": language_code,
        "alternative_language_codes": DEFAULT_STT_ALT_LANGUAGES,
        "enable_automatic_punctuation": True,
        "model": os.getenv("GOOGLE_STT_MODEL", "latest_short"),
        "encoding": encoding,
    }
    if DEFAULT_STT_PHRASES:
        config_kwargs["speech_contexts"] = [
            speech.SpeechContext(
                phrases=DEFAULT_STT_PHRASES,
                boost=float(os.getenv("GOOGLE_STT_PHRASE_BOOST", "15")),
            )
        ]
    if sample_rate_hertz:
        config_kwargs["sample_rate_hertz"] = sample_rate_hertz
    config = speech.RecognitionConfig(**config_kwargs)
    audio = speech.RecognitionAudio(content=audio_bytes)
    response = client.recognize(config=config, audio=audio)

    transcripts = []
    confidence = None
    for result in response.results:
        if not result.alternatives:
            continue
        alternative = result.alternatives[0]
        transcripts.append(alternative.transcript)
        if confidence is None:
            confidence = alternative.confidence

    transcript = " ".join(part.strip() for part in transcripts if part.strip()).strip()
    return {
        "transcript": transcript,
        "confidence": confidence,
        "language_code": language_code,
        "provider": "google-cloud-stt",
        "content_type": content_type,
    }


def _iso(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _parse_iso_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            try:
                parsed = datetime.strptime(str(value)[:19], "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _round(value, digits=1):
    if value is None:
        return None
    return round(float(value), digits)


def _sensor_row(row):
    if not row:
        return None
    return {
        "timestamp": _iso(row.get("timestamp")),
        "device_id": row.get("device_id"),
        "temperature_c": row.get("temperature_c"),
        "humidity_pct": row.get("humidity_pct"),
        "air_quality_index": row.get("air_quality_index"),
        "air_quality_label": row.get("air_quality_label"),
        "co2_source": row.get("co2_source"),
        "motion_detected": row.get("motion_detected"),
    }


CITY_ALIASES = {
    "geneva": ("Geneva", "CH"),
    "geneve": ("Geneva", "CH"),
    "genève": ("Geneva", "CH"),
    "lausanne": ("Lausanne", "CH"),
    "chavannes": ("Chavannes-pres-Renens", "CH"),
    "chavannes pres renens": ("Chavannes-pres-Renens", "CH"),
    "renens": ("Renens", "CH"),
    "zurich": ("Zurich", "CH"),
    "zürich": ("Zurich", "CH"),
    "bern": ("Bern", "CH"),
    "berne": ("Bern", "CH"),
    "montreux": ("Montreux", "CH"),
    "paris": ("Paris", "FR"),
    "lyon": ("Lyon", "FR"),
    "london": ("London", "GB"),
    "milan": ("Milan", "IT"),
}


LOCATION_STOP_WORDS = {
    "home", "house", "room", "inside", "indoor", "outside", "outdoor", "weather",
    "forecast", "temperature", "humidity", "co2", "today", "tomorrow", "yesterday", "week",
    "now", "please", "me", "the", "my", "station", "dashboard",
}


def _clean_city_candidate(value):
    city = str(value or "")
    city = re.split(
        r"\b(?:today|tomorrow|yesterday|this|next|now|please|outside|outdoor|weather|forecast|week|weekend|rain|raining)\b",
        city,
        flags=re.IGNORECASE,
    )[0]
    city = " ".join(city.replace("?", " ").replace(".", " ").replace(",", " ").split())
    city = city.strip(" -")
    if not city:
        return None
    normalized = normalize_question(city)
    if not normalized or normalized in LOCATION_STOP_WORDS:
        return None
    if all(part in LOCATION_STOP_WORDS for part in normalized.split()):
        return None
    return city


def _weather_location_from_question(question, device_id=None):
    """Return OpenWeather location kwargs requested in a natural-language question."""
    q = normalize_question(question)
    if not q:
        return {}

    for alias, (city, country_code) in CITY_ALIASES.items():
        if normalize_question(alias) in q:
            return {"city": city, "country_code": country_code}

    patterns = [
        r"\b(?:weather|forecast|temperature|rain|raining)\s+(?:in|at|for)\s+([a-zA-Z][a-zA-Z -]{2,35})",
        r"\b(?:in|at|for)\s+([a-zA-Z][a-zA-Z -]{2,35})",
    ]
    for pattern in patterns:
        match = re.search(pattern, str(question or ""), re.IGNORECASE)
        if not match:
            continue
        city = _clean_city_candidate(match.group(1))
        if city:
            return {"city": city, "country_code": None}

    match = re.search(r"\b(?:in|at|for|a|à)\s+([a-zA-Z][a-zA-Z -]{2,35})", str(question or ""), re.IGNORECASE)
    if match:
        city = match.group(1)
        city = re.split(r"\b(?:today|tomorrow|this|now|please|outside|weather|forecast)\b", city, flags=re.IGNORECASE)[0]
        city = _clean_city_candidate(city)
        if city:
            return {"city": city, "country_code": None}

    location = get_device_location(device_id)
    if location:
        return {"lat": location.get("lat"), "lon": location.get("lon")}

    location = get_ip_location()
    if location:
        return {"lat": location.get("lat"), "lon": location.get("lon")}

    return {}


def _stats(rows):
    if not rows:
        return {
            "count": 0,
            "temperature": {},
            "humidity": {},
            "air_quality": {},
            "motion_events": 0,
        }

    temps = [float(r["temperature_c"]) for r in rows if r.get("temperature_c") is not None]
    hums = [float(r["humidity_pct"]) for r in rows if r.get("humidity_pct") is not None]
    aqis = [
        float(r["air_quality_index"])
        for r in rows
        if r.get("air_quality_index") is not None and r.get("co2_source") == "sensor"
    ]
    motion_events = sum(1 for r in rows if r.get("motion_detected"))

    def summarize(values):
        if not values:
            return {}
        return {
            "min": _round(min(values)),
            "max": _round(max(values)),
            "avg": _round(sum(values) / len(values)),
        }

    return {
        "count": len(rows),
        "temperature": summarize(temps),
        "humidity": summarize(hums),
        "air_quality": summarize(aqis),
        "motion_events": motion_events,
        "first_timestamp": _iso(rows[0].get("timestamp")),
        "last_timestamp": _iso(rows[-1].get("timestamp")),
    }


def _latest_non_null(rows, field, source_field=None, source_value=None):
    for row in reversed(rows or []):
        if row.get(field) is None:
            continue
        if source_field and row.get(source_field) != source_value:
            continue
        return row
    return None


def build_context(device_id=None, hours=24, question=None):
    """Return recent sensor/weather data and summary statistics for the assistant."""
    bq = BigQueryClient()
    weather_service = WeatherService()
    weather_location = _weather_location_from_question(question, device_id=device_id)
    latest = _sensor_row(bq.get_latest_sensor_reading(device_id=device_id))
    history = [_sensor_row(row) for row in bq.get_sensor_history(device_id=device_id, hours=hours)]
    history = [row for row in history if row]
    all_history = history
    if device_id:
        all_history = [_sensor_row(row) for row in bq.get_sensor_history(device_id=None, hours=hours)]
        all_history = [row for row in all_history if row]
    current_weather = weather_service.get_current_weather(**weather_location)
    forecast = weather_service.get_forecast(days=3, **weather_location)
    latest_temperature = _latest_non_null(history, "temperature_c") or _latest_non_null(all_history, "temperature_c")
    latest_humidity = _latest_non_null(history, "humidity_pct") or _latest_non_null(all_history, "humidity_pct")
    latest_co2 = _latest_non_null(history, "air_quality_index", "co2_source", "sensor") or _latest_non_null(
        all_history,
        "air_quality_index",
        "co2_source",
        "sensor",
    )
    return {
        "device_id": device_id or "all devices",
        "hours": hours,
        "latest": latest,
        "latest_temperature": latest_temperature,
        "latest_humidity": latest_humidity,
        "latest_co2": latest_co2,
        "stats": _stats(history),
        "all_device_stats": _stats(all_history),
        "history_rows": history,
        "recent_rows": history[-20:],
        "weather_location": weather_location,
        "current_weather": current_weather.to_dict() if current_weather else None,
        "forecast": [day.__dict__ for day in forecast],
    }


def build_context_prompt(question, context):
    return f"""
You are a concise cloud analytics assistant for an IoT weather station project.
Answer using only the provided indoor sensor and outdoor weather data.
If the data is insufficient, say what is missing.
Use Celsius for temperature and percent for humidity.
Answer in one or two complete, natural sentences.
Do not answer with only keywords or fragments.

Question:
{question}

Data context:
{context}
""".strip()


def normalize_question(question):
    """Normalize STT text so intent matching survives small recognition changes."""
    text = str(question or "").lower()
    replacements = {
        "é": "e", "è": "e", "ê": "e", "ë": "e",
        "à": "a", "â": "a", "ä": "a",
        "ù": "u", "û": "u", "ü": "u",
        "ô": "o", "ö": "o",
        "î": "i", "ï": "i",
        "ç": "c",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"[^a-z0-9% ]+", " ", text)
    return " ".join(text.split())


def detect_intent(question):
    q = normalize_question(question)
    scores = {}
    for intent, keywords in INTENT_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            key = normalize_question(keyword)
            if key and key in q:
                score += 2 if " " in key else 1
        if score:
            scores[intent] = score

    if not scores:
        return "general"

    if scores.get("historical") and (
        scores.get("humidity")
        or scores.get("temperature")
        or scores.get("co2")
        or scores.get("motion")
        or scores.get("average")
    ):
        return "historical"
    if scores.get("rain_forecast"):
        return "rain_forecast"
    if scores.get("outfit"):
        return "outfit"
    if scores.get("ventilation"):
        return "ventilation"
    if scores.get("co2"):
        return "co2"
    if scores.get("humidity") and scores.get("room_health"):
        return "room_health"
    if scores.get("room_health"):
        return "room_health"
    if scores.get("humidity"):
        return "humidity"
    if scores.get("temperature") and not scores.get("outdoor_weather"):
        return "temperature"
    if scores.get("motion"):
        return "motion"
    if scores.get("average"):
        return "average"
    if scores.get("outdoor_weather") or scores.get("temperature"):
        return "outdoor_weather"
    return max(scores, key=scores.get)


def _weather_place(weather):
    if not weather:
        return "outside"
    return weather.get("city") or "outside"


def _forecast_rain_answer(forecast, weather=None):
    place = _weather_place(weather)
    rainy_days = []
    for day in forecast or []:
        main = str(day.get("weather_main") or day.get("weather_description") or "")
        if any(word in main.lower() for word in ["rain", "drizzle", "storm"]):
            date = str(day.get("date") or "")
            label = date[5:10] if len(date) >= 10 else "one forecast day"
            rainy_days.append(label)

    if rainy_days:
        return "Yes. Rain is expected in " + place + " on " + ", ".join(rainy_days[:3]) + ", so bring an umbrella."
    if forecast:
        return "No rain appears in the available forecast for " + place + ". It looks mostly dry."
    return "I do not have forecast data yet, so I cannot confirm rain."


def _forecast_summary_answer(forecast, weather=None):
    place = _weather_place(weather)
    if not forecast:
        return "I do not have forecast data yet."
    parts = []
    for day in forecast[:3]:
        date = str(day.get("date") or "")
        label = date[5:10] if len(date) >= 10 else "next day"
        main = day.get("weather_main") or day.get("weather_description") or "weather"
        low = day.get("temp_min")
        high = day.get("temp_max")
        parts.append(f"{label}: {main}, {low} to {high} C")
    return "Forecast for " + place + ": " + "; ".join(parts) + "."


def _outfit_answer(weather):
    if not weather:
        return "Outdoor weather is unavailable, so take a light layer just in case."
    place = _weather_place(weather)
    desc = str(weather.get("weather_main") or weather.get("weather_description") or "").lower()
    temp = weather.get("temperature_c")
    try:
        temp_num = float(temp)
    except (TypeError, ValueError):
        temp_num = None

    if any(word in desc for word in ["rain", "drizzle", "storm"]):
        return f"It is {temp} C in {place} with rain risk, so take an umbrella or rain jacket."
    if temp_num is not None and temp_num >= 24:
        return f"It is {temp} C in {place}, so wear light clothes, sunglasses, and sunscreen."
    if temp_num is not None and temp_num <= 10:
        return f"It is {temp} C in {place}, so wear a warm jacket or layers."
    if temp_num is not None and temp_num <= 16:
        return f"It is {temp} C in {place}, so a light jacket or layers are a good idea."
    return f"It is {temp} C in {place} with {desc or 'stable weather'}, so dress comfortably."


def _ventilation_answer(context):
    weather = context.get("current_weather")
    latest_humidity = context.get("latest_humidity") or {}
    hum = latest_humidity.get("humidity_pct")
    desc = str((weather or {}).get("weather_main") or "").lower()

    if hum is None:
        return "I need a recent indoor humidity reading before advising on ventilation."
    try:
        hum_num = float(hum)
    except (TypeError, ValueError):
        hum_num = None

    if hum_num is not None and hum_num > 65:
        if "rain" in desc:
            return "Ventilate briefly if needed, but close it soon because it is raining outside."
        return "Yes, open the window for a few minutes because indoor humidity is high."
    if hum_num is not None and hum_num < 40:
        return "No. The room is already dry, so opening the window may make comfort worse."
    return "Ventilation is optional right now; indoor humidity looks comfortable."


def _room_health_answer(context):
    latest_temperature = context.get("latest_temperature") or {}
    latest_humidity = context.get("latest_humidity") or {}
    latest_co2 = context.get("latest_co2") or {}
    temp = latest_temperature.get("temperature_c")
    hum = latest_humidity.get("humidity_pct")
    co2 = latest_co2.get("air_quality_index")

    issues = []
    try:
        if hum is not None and float(hum) < 40:
            issues.append(f"humidity is low at {hum}%")
        elif hum is not None and float(hum) > 65:
            issues.append(f"humidity is high at {hum}%")
    except (TypeError, ValueError):
        pass
    try:
        if temp is not None and float(temp) < 18:
            issues.append(f"temperature is cool at {temp} C")
        elif temp is not None and float(temp) > 26:
            issues.append(f"temperature is warm at {temp} C")
    except (TypeError, ValueError):
        pass
    try:
        if co2 is not None and float(co2) > 1000:
            issues.append(f"CO2 is high at {co2} ppm")
    except (TypeError, ValueError):
        pass

    if issues:
        return "Room needs attention: " + ", ".join(issues[:2]) + "."
    if temp is not None or hum is not None or co2 is not None:
        return f"Room looks healthy: {temp or 'no temp'} C, {hum or 'no humidity'}% humidity, CO2 {co2 or 'not measured'}."
    return "I need recent indoor readings before judging room health."


def _required_history_hours(question, current_hours=24):
    q = normalize_question(question)
    required = current_hours or 24
    if "last week" in q or "week" in q or "semaine" in q:
        required = max(required, 168)
    if "yesterday" in q or "hier" in q:
        required = max(required, 48)
    if "today" in q or "aujourd hui" in q:
        required = max(required, 24)

    day_match = re.search(r"(\d+)\s*(day|days|jour|jours)\s*(ago|avant)?", q)
    if day_match:
        days = int(day_match.group(1))
        required = max(required, (days + 1) * 24)

    hour_match = re.search(r"last\s*(\d+)\s*(hour|hours)", q)
    if hour_match:
        required = max(required, int(hour_match.group(1)))

    return min(max(required, 24), 24 * 14)


def _history_period(question):
    q = normalize_question(question)
    if "yesterday" in q or "hier" in q:
        return 24, 48, "yesterday"
    if "today" in q or "aujourd hui" in q:
        return 0, 24, "today"
    day_match = re.search(r"(\d+)\s*(day|days|jour|jours)\s*(ago|avant)?", q)
    if day_match:
        days = int(day_match.group(1))
        if days <= 0:
            return 0, 24, "today"
        return days * 24, (days + 1) * 24, f"{days} day(s) ago"
    hour_match = re.search(r"last\s*(\d+)\s*(hour|hours)", q)
    if hour_match:
        hours = int(hour_match.group(1))
        return 0, hours, f"the last {hours} hours"
    return 0, None, f"the last {q or 'selected'} period"


def _rows_for_period(rows, min_age_hours, max_age_hours):
    now = datetime.utcnow()
    selected = []
    for row in rows or []:
        timestamp = _parse_iso_datetime(row.get("timestamp"))
        if not timestamp:
            continue
        age_hours = (now - timestamp).total_seconds() / 3600.0
        if age_hours < min_age_hours:
            continue
        if max_age_hours is not None and age_hours >= max_age_hours:
            continue
        selected.append(row)
    return selected


def _question_field(question):
    q = normalize_question(question)
    if "humidity" in q or "humidite" in q or "humid" in q:
        return "humidity_pct", "humidity", "%"
    if "co2" in q or "air quality" in q or "ppm" in q or "qualite" in q:
        return "air_quality_index", "CO2", " ppm"
    if "motion" in q or "presence" in q or "movement" in q or "mouvement" in q:
        return "motion_detected", "motion", ""
    return "temperature_c", "temperature", " C"


def _extract_threshold(question):
    q = normalize_question(question)
    match = re.search(r"(\d+(?:\.\d+)?)\s*(%|percent|ppm|c|degrees)?", q)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _comparison_mode(question):
    q = normalize_question(question)
    if any(word in q for word in ["below", "under", "less", "lower", "moins", "sous"]):
        return "below"
    if any(word in q for word in ["exceed", "exceeded", "above", "over", "higher", "more", "depasse", "plus"]):
        return "above"
    return None


def _historical_answer(question, context):
    q = normalize_question(question)
    if not any(word in q for word in ["yesterday", "today", "ago", "last", "history", "historical", "exceed", "above", "below", "over", "under", "hier", "jours", "depasse"]):
        return None

    rows = context.get("history_rows") or []
    min_age, max_age, label = _history_period(question)
    rows = _rows_for_period(rows, min_age, max_age)
    field, field_label, unit = _question_field(question)

    if not rows:
        return f"I do not have {field_label} data for {label}."

    if field == "motion_detected":
        count = sum(1 for row in rows if row.get("motion_detected"))
        return f"Motion was detected {count} time(s) {label}."

    values = []
    for row in rows:
        value = row.get(field)
        if value is not None:
            try:
                values.append(float(value))
            except (TypeError, ValueError):
                pass

    if not values:
        return f"I do not have {field_label} readings for {label}."

    threshold = _extract_threshold(question)
    comparison = _comparison_mode(question)
    if threshold is not None and comparison:
        if comparison == "above":
            count = sum(1 for value in values if value > threshold)
            did = count > 0
            word = "exceeded"
        else:
            count = sum(1 for value in values if value < threshold)
            did = count > 0
            word = "went below"
        answer = "Yes" if did else "No"
        return (
            f"{answer}. {field_label.capitalize()} {word} {threshold:g}{unit} "
            f"{count} time(s) {label}. Range: {round(min(values), 1)} to {round(max(values), 1)}{unit}."
        )

    avg = round(sum(values) / len(values), 1)
    return (
        f"For {label}, {field_label} averaged {avg}{unit}, "
        f"with a range from {round(min(values), 1)} to {round(max(values), 1)}{unit}."
    )


def deterministic_answer(question, context):
    """Answer common dashboard/Core2 intents with stable analytics logic."""
    intent = detect_intent(question)
    weather = context.get("current_weather")
    forecast = context.get("forecast") or []
    stats = context.get("stats", {})

    historical = _historical_answer(question, context)
    if historical:
        return historical

    if intent == "rain_forecast":
        return _forecast_rain_answer(forecast, weather)
    if intent == "outfit":
        return _outfit_answer(weather)
    if intent == "ventilation":
        return _ventilation_answer(context)
    if intent == "room_health":
        return _room_health_answer(context)
    if intent == "outdoor_weather":
        if not weather:
            return "Outdoor weather is unavailable right now."
        q = normalize_question(question)
        if any(word in q for word in ["forecast", "tomorrow", "week", "weekend", "prevision"]):
            return _forecast_summary_answer(forecast, weather)
        temp = weather.get("temperature_c")
        desc = weather.get("weather_description") or weather.get("weather_main", "weather")
        city = weather.get("city") or "outside"
        wind = weather.get("wind_speed_ms")
        return f"Outside in {city}: {temp} C, {desc}, wind {wind} m/s."
    if intent == "humidity":
        latest_humidity = context.get("latest_humidity") or {}
        latest_hum = latest_humidity.get("humidity_pct")
        if latest_hum is None:
            return "No recent humidity reading is available."
        return f"The latest indoor humidity is {latest_hum}%."
    if intent == "temperature":
        latest_temperature = context.get("latest_temperature") or {}
        latest_temp = latest_temperature.get("temperature_c")
        if latest_temp is None:
            return "No recent indoor temperature reading is available."
        return f"The latest indoor temperature is {latest_temp} C."
    if intent == "co2":
        latest_co2 = context.get("latest_co2") or {}
        latest_aqi = latest_co2.get("air_quality_index")
        if latest_aqi is None:
            return "No real CO2 reading is available in this period."
        return f"The latest CO2 reading is {latest_aqi} ppm."
    if intent == "motion":
        return f"Motion was detected {stats.get('motion_events', 0)} time(s) over the last {context.get('hours')} hours."
    if intent == "average":
        return fallback_answer(question, context)
    return None


def _generate_with_gemini(question, context):
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return None

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    prompt = build_context_prompt(question, context)
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=(
                    "Answer as a concise cloud analytics assistant for a weather station dashboard. "
                    "Use only the provided sensor data. Be practical and demo-friendly. "
                    "Use one or two complete natural sentences, not keyword lists."
                ),
                temperature=0.3,
                max_output_tokens=300,
                http_options=types.HttpOptions(timeout=LLM_TIMEOUT_SECONDS * 1000),
            ),
        )
    except TypeError:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=(
                    "Answer as a concise cloud analytics assistant for a weather station dashboard. "
                    "Use only the provided sensor data. Be practical and demo-friendly. "
                    "Use one or two complete natural sentences, not keyword lists."
                ),
                temperature=0.3,
                max_output_tokens=300,
            ),
        )
    return response.text.strip(), GEMINI_MODEL


def fallback_answer(question, context):
    """Return a useful answer when no LLM key is configured."""
    latest = context.get("latest")
    stats = context.get("stats", {})
    q = question.lower()
    weather = context.get("current_weather")
    forecast = context.get("forecast") or []

    deterministic = deterministic_answer(question, context)
    if deterministic:
        return deterministic

    if "outside" in q or "outdoor" in q or "weather" in q or "forecast" in q:
        if not weather:
            return "Outdoor weather is unavailable right now."
        temp = weather.get("temperature_c")
        desc = weather.get("weather_description") or weather.get("weather_main", "weather")
        city = weather.get("city") or "outside"
        wind = weather.get("wind_speed_ms")
        forecast_note = ""
        if forecast:
            next_day = forecast[0]
            forecast_note = (
                f" Forecast: {next_day.get('weather_main')} "
                f"{next_day.get('temp_min')} to {next_day.get('temp_max')} C."
            )
        return f"Outside in {city}: {temp} C, {desc}, wind {wind} m/s.{forecast_note}"

    if not latest and not stats.get("count"):
        return "I do not have recent sensor data for that question yet. Let the Core2 collect a few readings first."

    if "average" in q or "avg" in q or "mean" in q:
        parts = []
        temp_avg = stats.get("temperature", {}).get("avg")
        hum_avg = stats.get("humidity", {}).get("avg")
        aqi_avg = stats.get("air_quality", {}).get("avg")
        if temp_avg is not None:
            parts.append(f"average temperature was {temp_avg} C")
        if hum_avg is not None:
            parts.append(f"average humidity was {hum_avg}%")
        if aqi_avg is not None:
            parts.append(f"average CO2 was {aqi_avg} ppm")
        return "Over the selected period, the " + ", and the ".join(parts) + "."

    if "motion" in q:
        return f"Motion was detected {stats.get('motion_events', 0)} time(s) over the last {context.get('hours')} hours."

    if "humidity" in q:
        hum = stats.get("humidity", {})
        latest_humidity = context.get("latest_humidity") or {}
        latest_hum = latest_humidity.get("humidity_pct")
        if latest_hum is None:
            return "No recent humidity reading is available in this period."
        return (
            f"The latest humidity is {latest_hum}%. "
            f"Over the last {context.get('hours')} hours, humidity ranged from "
            f"{hum.get('min')}% to {hum.get('max')}%, with an average of {hum.get('avg')}%."
        )

    if "temperature" in q or "temp" in q:
        temp = stats.get("temperature", {})
        latest_temperature = context.get("latest_temperature") or {}
        latest_temp = latest_temperature.get("temperature_c")
        if latest_temp is None:
            return "No recent temperature reading is available in this period."
        return (
            f"The latest temperature is {latest_temp} C. "
            f"Over the last {context.get('hours')} hours, temperature ranged from "
            f"{temp.get('min')} C to {temp.get('max')} C, with an average of {temp.get('avg')} C."
        )

    if "air" in q or "aqi" in q or "quality" in q or "co2" in q:
        aqi = stats.get("air_quality", {})
        latest_co2 = context.get("latest_co2") or {}
        latest_aqi = latest_co2.get("air_quality_index")
        if latest_aqi is None:
            return "No real CO2 reading is available in this period."
        return (
            f"The latest CO2 reading is {latest_aqi} ppm. "
            f"Over the last {context.get('hours')} hours, it ranged from "
            f"{aqi.get('min')} to {aqi.get('max')} ppm, with an average of {aqi.get('avg')} ppm."
        )

    if latest:
        latest_temperature = context.get("latest_temperature") or {}
        latest_humidity = context.get("latest_humidity") or {}
        latest_co2 = context.get("latest_co2") or {}
        return (
            f"Recent readings for {context.get('device_id')}: "
            f"{latest_temperature.get('temperature_c')} C, {latest_humidity.get('humidity_pct')}% humidity, "
            f"CO2 {latest_co2.get('air_quality_index') or 'not measured'}, "
            f"motion {'detected' if latest.get('motion_detected') else 'not detected'}."
        )

    return "I found data, but I need a more specific question to summarize it."


def generate_response(question, context):
    """Generate an assistant answer using Gemini, with local analytics fallback."""
    deterministic = deterministic_answer(question, context)
    if deterministic:
        return deterministic, "local-intent"

    errors = []

    try:
        gemini_result = _generate_with_gemini(question, context)
        if gemini_result:
            return gemini_result
    except Exception as exc:
        errors.append(f"Gemini failed: {exc}")

    source = "local-fallback"
    answer = fallback_answer(question, context)
    if errors:
        source = "local-fallback-after-error"
    return answer, source


def answer_question(question, device_id=None, hours=24):
    if not question or not question.strip():
        raise ValueError("Question is required.")

    hours = _required_history_hours(question, hours)
    context = build_context(device_id=device_id, hours=hours, question=question)
    answer, source = generate_response(question.strip(), context)
    return {
        "answer": answer,
        "source": source,
        "context": context,
        "generated_at": datetime.utcnow().isoformat(),
    }
