"""Voice and assistant service."""

import os
import base64
from io import BytesIO
from datetime import datetime
import wave
import subprocess
import tempfile

from dotenv import load_dotenv

from data.bigquery_client import BigQueryClient
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
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_TTS_MODEL = os.getenv("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")
GEMINI_TTS_VOICE = os.getenv("GEMINI_TTS_VOICE", "Kore")
GEMINI_TTS_GAIN = float(os.getenv("GEMINI_TTS_GAIN", "3.0"))
GOOGLE_TTS_GAIN = float(os.getenv("GOOGLE_TTS_GAIN", "2.0"))
WINDOWS_TTS_GAIN = float(os.getenv("WINDOWS_TTS_GAIN", "1.8"))
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "12"))


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


def build_context(device_id=None, hours=24):
    """Return recent sensor/weather data and summary statistics for the assistant."""
    bq = BigQueryClient()
    weather_service = WeatherService()
    latest = _sensor_row(bq.get_latest_sensor_reading(device_id=device_id))
    history = [_sensor_row(row) for row in bq.get_sensor_history(device_id=device_id, hours=hours)]
    history = [row for row in history if row]
    current_weather = weather_service.get_current_weather()
    forecast = weather_service.get_forecast(days=3)
    latest_temperature = _latest_non_null(history, "temperature_c")
    latest_humidity = _latest_non_null(history, "humidity_pct")
    latest_co2 = _latest_non_null(history, "air_quality_index", "co2_source", "sensor")
    return {
        "device_id": device_id or "all devices",
        "hours": hours,
        "latest": latest,
        "latest_temperature": latest_temperature,
        "latest_humidity": latest_humidity,
        "latest_co2": latest_co2,
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
Answer in one or two complete, natural sentences.
Do not answer with only keywords or fragments.

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

    context = build_context(device_id=device_id, hours=hours)
    answer, source = generate_response(question.strip(), context)
    return {
        "answer": answer,
        "source": source,
        "context": context,
        "generated_at": datetime.utcnow().isoformat(),
    }
