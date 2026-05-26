"""Assistant and future voice routes."""

from io import BytesIO
import time

from flask import Blueprint, jsonify, request, send_file

from services.voice_service import (
    answer_question,
    deterministic_answer,
    fallback_answer,
    synthesize_speech,
    transcribe_speech,
)

voice_bp = Blueprint("voice_bp", __name__)


# Shorten and clean assistant text for the Core2 display.
def _device_safe_text(text, max_chars=80):
    replacements = {
        "Ã©": "e",
        "Ã¨": "e",
        "Ãª": "e",
        "Ã ": "a",
        "Ã§": "c",
        "Â°": " degrees ",
        "/": " per ",
    }
    value = str(text or "")
    for old, new in replacements.items():
        value = value.replace(old, new)
    value = " ".join(value.replace("\n", " ").split())
    if len(value) > max_chars:
        value = value[: max_chars - 3].rstrip(" ,.;:") + "..."
    return value


# Keep spoken Core2 answers short but sentence-like.
def _complete_device_sentence(text, max_chars=140):
    value = _device_safe_text(text, max_chars=max_chars * 2)
    if len(value) <= max_chars:
        if value and value[-1] not in ".!?":
            value += "."
        return value

    cutoff = -1
    for mark in [". ", "! ", "? "]:
        position = value.rfind(mark, 0, max_chars)
        if position > cutoff:
            cutoff = position + 1

    if cutoff >= 35:
        return value[:cutoff].strip()

    shortened = value[:max_chars].rstrip(" ,.;:")
    return shortened + "."


# Prepare a short version of an answer for TTS.
def _speech_summary(text, question="", max_chars=70):
    q = str(question or "").lower()
    value = _device_safe_text(text, max_chars=180)

    if any(word in q for word in ["outside", "outdoor", "weather", "forecast"]):
        parts = value.split(". ")
        if parts and parts[0].strip():
            value = parts[0].strip() + "."
    elif any(word in q for word in ["humidity", "co2", "air", "quality", "motion", "ventilate"]):
        parts = value.split(". ")
        if parts and parts[0].strip():
            value = parts[0].strip() + "."

    return _complete_device_sentence(value, max_chars=max_chars)


# Retry TTS once when the first synthesis attempt fails.
def _synthesize_with_retry(text, attempts=2):
    last_error = None
    for attempt in range(attempts):
        try:
            return synthesize_speech(text=text)
        except Exception as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(0.8)
    raise last_error


# API route that converts text into speech audio.
@voice_bp.route("/tts", methods=["POST"])
def text_to_speech():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    language_code = data.get("language_code") or None
    voice_name = data.get("voice_name") or None

    try:
        audio, mimetype, provider = synthesize_speech(
            text=text,
            language_code=language_code,
            voice_name=voice_name,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Text-to-speech failed: {exc}"}), 500

    response = send_file(
        BytesIO(audio),
        mimetype=mimetype,
        as_attachment=False,
        download_name="weather-assistant.mp3",
    )
    response.headers["X-TTS-Provider"] = provider
    return response


# Core2-friendly TTS route with short WAV output.
@voice_bp.route("/device-tts", methods=["GET"])
def device_text_to_speech():
    text = _device_safe_text(request.args.get("text", ""), max_chars=180)

    try:
        audio, mimetype, provider = _synthesize_with_retry(text=text)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Device text-to-speech failed: {exc}"}), 500

    response = send_file(
        BytesIO(audio),
        mimetype=mimetype,
        as_attachment=False,
        download_name="assistant.wav",
    )
    response.headers["X-TTS-Provider"] = provider
    return response


# API route that transcribes uploaded speech audio.
@voice_bp.route("/stt", methods=["POST"])
def speech_to_text():
    audio_file = request.files.get("audio")
    language_code = request.form.get("language_code") or request.args.get("language_code") or None

    if audio_file:
        audio_bytes = audio_file.read()
        content_type = audio_file.content_type
    else:
        audio_bytes = request.get_data()
        content_type = request.content_type

    try:
        result = transcribe_speech(
            audio_bytes=audio_bytes,
            language_code=language_code,
            content_type=content_type,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Speech-to-text failed: {exc}"}), 500

    return jsonify(result), 200


# Core2-friendly route that transcribes raw device audio.
@voice_bp.route("/device-stt", methods=["POST"])
def device_speech_to_text():
    """Speech-to-text endpoint for Core2/UIFlow.

    Send raw WAV bytes in the request body. Optional query param:
    ?language_code=en-US or fr-FR
    """
    language_code = request.args.get("language_code") or request.form.get("language_code") or None
    audio_bytes = request.get_data()
    content_type = request.content_type or "audio/wav"

    try:
        result = transcribe_speech(
            audio_bytes=audio_bytes,
            language_code=language_code,
            content_type=content_type,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Device speech-to-text failed: {exc}"}), 500

    return jsonify(result), 200


# Transcribe Core2 audio, answer it, and return short device text.
@voice_bp.route("/device-audio-question", methods=["POST"])
def device_audio_question():
    """Core2 endpoint: raw WAV audio -> transcript -> assistant answer."""
    language_code = request.args.get("language_code") or request.form.get("language_code") or None
    device_id = request.args.get("device_id") or request.form.get("device_id") or None
    content_type = request.content_type or "audio/wav"
    audio_bytes = request.get_data()

    try:
        hours = int(request.args.get("hours") or request.form.get("hours") or 24)
    except (TypeError, ValueError):
        hours = 24

    try:
        stt_result = transcribe_speech(
            audio_bytes=audio_bytes,
            language_code=language_code,
            content_type=content_type,
        )
        transcript = stt_result.get("transcript", "").strip()
        if not transcript:
            return jsonify({
                "error": "No speech detected.",
                "transcript": "",
                "provider": stt_result.get("provider", "google-cloud-stt"),
            }), 422

        answer_result = answer_question(
            question=transcript,
            device_id=device_id,
            hours=hours,
        )
        answer = answer_result.get("answer", "")
        broken_answer = len(answer.strip()) < 24 or answer.strip().endswith((",", ":", ";"))
        stable_answer = deterministic_answer(transcript, answer_result.get("context", {}))
        if stable_answer:
            answer = stable_answer
        elif broken_answer:
            answer = fallback_answer(transcript, answer_result.get("context", {}))
        speech = _speech_summary(answer, question=transcript, max_chars=145)
        return jsonify({
            "transcript": transcript,
            "answer": answer,
            "speech": speech,
            "source": answer_result.get("source", "unknown"),
            "stt_provider": stt_result.get("provider", "google-cloud-stt"),
            "confidence": stt_result.get("confidence"),
        }), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Device audio question failed: {exc}"}), 500


# API route that answers a typed dashboard question.
@voice_bp.route("/ask", methods=["POST"])
def ask_llm():
    data = request.get_json(silent=True) or {}
    question = data.get("question", "")
    device_id = data.get("device_id") or None

    try:
        hours = int(data.get("hours", 24))
    except (TypeError, ValueError):
        hours = 24

    try:
        result = answer_question(question=question, device_id=device_id, hours=hours)
        return jsonify(result), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Assistant failed: {exc}"}), 500


# API route that returns a short spoken comfort summary.
@voice_bp.route("/device-summary", methods=["GET", "POST"])
def device_summary():
    data = request.get_json(silent=True) or {}
    device_id = data.get("device_id") or request.args.get("device_id") or None
    question = data.get("question") or request.args.get("question") or (
        "Give a short spoken recommendation for home comfort using the latest indoor "
        "temperature, humidity, motion, outdoor weather, and forecast. Mention umbrella "
        "or ventilation only if useful. Answer in one short sentence."
    )

    try:
        hours = int(data.get("hours") or request.args.get("hours") or 24)
    except (TypeError, ValueError):
        hours = 24

    try:
        result = answer_question(question=question, device_id=device_id, hours=hours)
        answer = result.get("answer", "")
        broken_answer = len(answer.strip()) < 24 or answer.strip().endswith((",", ":", ";"))
        stable_answer = deterministic_answer(question, result.get("context", {}))
        if stable_answer:
            answer = stable_answer
        elif broken_answer:
            answer = fallback_answer(question, result.get("context", {}))
        speech = _speech_summary(answer, question=question)
        return jsonify({
            "answer": answer,
            "speech": speech,
            "source": result.get("source", "unknown"),
        }), 200
    except Exception as exc:
        return jsonify({"error": f"Device assistant failed: {exc}"}), 500
