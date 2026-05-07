"""Assistant and future voice routes."""

from io import BytesIO
import time

from flask import Blueprint, jsonify, request, send_file

from services.voice_service import answer_question, fallback_answer, synthesize_speech

voice_bp = Blueprint("voice_bp", __name__)


def _device_safe_text(text, max_chars=80):
    replacements = {
        "é": "e",
        "è": "e",
        "ê": "e",
        "à": "a",
        "ç": "c",
        "°": " degrees ",
        "/": " per ",
    }
    value = str(text or "")
    for old, new in replacements.items():
        value = value.replace(old, new)
    value = " ".join(value.replace("\n", " ").split())
    if len(value) > max_chars:
        value = value[: max_chars - 3].rstrip(" ,.;:") + "..."
    return value


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

    return _device_safe_text(value, max_chars=max_chars)


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


@voice_bp.route("/device-tts", methods=["GET"])
def device_text_to_speech():
    text = _device_safe_text(request.args.get("text", ""), max_chars=80)

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


@voice_bp.route("/stt", methods=["POST"])
def speech_to_text():
    return jsonify({"message": "Speech-to-text is not implemented yet"}), 501


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
        q = question.lower()
        broken_answer = len(answer.strip()) < 24 or answer.strip().endswith((",", ":", ";"))
        deterministic_question = any(word in q for word in ["outside", "outdoor", "weather", "forecast"])
        if deterministic_question or broken_answer:
            answer = fallback_answer(question, result.get("context", {}))
        speech = _speech_summary(answer, question=question)
        return jsonify({
            "answer": answer,
            "speech": speech,
            "source": result.get("source", "unknown"),
        }), 200
    except Exception as exc:
        return jsonify({"error": f"Device assistant failed: {exc}"}), 500
