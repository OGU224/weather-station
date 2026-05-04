"""Voice and assistant service."""

import os
import base64
from io import BytesIO
from datetime import datetime
import wave

from dotenv import load_dotenv

from data.bigquery_client import BigQueryClient
from services.weather_service import WeatherService

load_dotenv(override=True)

DEFAULT_TTS_LANGUAGE = os.getenv("GOOGLE_TTS_LANGUAGE", "en-US")
DEFAULT_TTS_VOICE = os.getenv("GOOGLE_TTS_VOICE", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_TTS_MODEL = os.getenv("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")
GEMINI_TTS_VOICE = os.getenv("GEMINI_TTS_VOICE", "Kore")
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "12"))


def _wav_bytes_from_pcm(pcm_data, channels=1, rate=24000, sample_width=2):
    buffer = BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(rate)
        wav_file.writeframes(pcm_data)
    return buffer.getvalue()


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


def synthesize_speech(text, language_code=None, voice_name=None):
    """Return WAV audio bytes from Gemini native TTS."""
    if not text or not text.strip():
        raise ValueError("Text is required.")

    text = text.strip()

    try:
        gemini_result = _synthesize_with_gemini(text)
        if gemini_result:
            return gemini_result
    except Exception as exc:
        raise RuntimeError(f"Gemini TTS failed: {exc}") from exc

    raise RuntimeError("GEMINI_API_KEY is not configured.")


def _iso(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


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
        "motion_detected": row.get("motion_detected"),
    }


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
    aqis = [float(r["air_quality_index"]) for r in rows if r.get("air_quality_index") is not None]
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


def build_context(device_id=None, hours=24):
    """Return recent sensor/weather data and summary statistics for the assistant."""
    bq = BigQueryClient()
    weather_service = WeatherService()
    latest = _sensor_row(bq.get_latest_sensor_reading(device_id=device_id))
    history = [_sensor_row(row) for row in bq.get_sensor_history(device_id=device_id, hours=hours)]
    history = [row for row in history if row]
    current_weather = weather_service.get_current_weather()
    forecast = weather_service.get_forecast(days=3)
    return {
        "device_id": device_id or "all devices",
        "hours": hours,
        "latest": latest,
        "stats": _stats(history),
        "recent_rows": history[-20:],
        "current_weather": current_weather.to_dict() if current_weather else None,
        "forecast": [day.__dict__ for day in forecast],
    }


def build_context_prompt(question, context):
    return f"""
You are a concise cloud analytics assistant for an IoT weather station project.
Answer using only the provided indoor sensor and outdoor weather data.
If the data is insufficient, say what is missing.
Use Celsius for temperature and percent for humidity.

Question:
{question}

Data context:
{context}
""".strip()


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
                    "Use only the provided sensor data. Be practical and demo-friendly."
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
                    "Use only the provided sensor data. Be practical and demo-friendly."
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
            parts.append(f"average air quality value was {aqi_avg}")
        return "Over the selected period, the " + ", and the ".join(parts) + "."

    if "motion" in q:
        return f"Motion was detected {stats.get('motion_events', 0)} time(s) over the last {context.get('hours')} hours."

    if "humidity" in q:
        hum = stats.get("humidity", {})
        latest_hum = latest.get("humidity_pct") if latest else None
        return (
            f"The latest humidity is {latest_hum}%. "
            f"Over the last {context.get('hours')} hours, humidity ranged from "
            f"{hum.get('min')}% to {hum.get('max')}%, with an average of {hum.get('avg')}%."
        )

    if "temperature" in q or "temp" in q:
        temp = stats.get("temperature", {})
        latest_temp = latest.get("temperature_c") if latest else None
        return (
            f"The latest temperature is {latest_temp} C. "
            f"Over the last {context.get('hours')} hours, temperature ranged from "
            f"{temp.get('min')} C to {temp.get('max')} C, with an average of {temp.get('avg')} C."
        )

    if "air" in q or "aqi" in q or "quality" in q:
        aqi = stats.get("air_quality", {})
        latest_aqi = latest.get("air_quality_index") if latest else None
        return (
            f"The latest air quality value is {latest_aqi}. "
            f"Over the last {context.get('hours')} hours, it ranged from "
            f"{aqi.get('min')} to {aqi.get('max')}, with an average of {aqi.get('avg')}."
        )

    if latest:
        return (
            f"Latest reading for {latest.get('device_id')}: "
            f"{latest.get('temperature_c')} C, {latest.get('humidity_pct')}% humidity, "
            f"air quality {latest.get('air_quality_index')}, "
            f"motion {'detected' if latest.get('motion_detected') else 'not detected'}."
        )

    return "I found data, but I need a more specific question to summarize it."


def generate_response(question, context):
    """Generate an assistant answer using Gemini, with local analytics fallback."""
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
        answer = f"{answer} LLM fallback details: {'; '.join(errors)}"
    return answer, source


def answer_question(question, device_id=None, hours=24):
    if not question or not question.strip():
        raise ValueError("Question is required.")

    context = build_context(device_id=device_id, hours=hours)
    answer, source = generate_response(question.strip(), context)
    return {
        "answer": answer,
        "source": source,
        "context": context,
        "generated_at": datetime.utcnow().isoformat(),
    }
