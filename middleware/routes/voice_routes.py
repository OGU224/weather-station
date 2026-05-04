"""Assistant and future voice routes."""

from io import BytesIO

from flask import Blueprint, jsonify, request, send_file

from services.voice_service import answer_question, synthesize_speech

voice_bp = Blueprint("voice_bp", __name__)


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
    text = request.args.get("text", "")
    if len(text) > 120:
        text = text[:117].rstrip() + "..."

    try:
        audio, mimetype, provider = synthesize_speech(text=text)
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
        return jsonify({
            "answer": result.get("answer", ""),
            "source": result.get("source", "unknown"),
        }), 200
    except Exception as exc:
        return jsonify({"error": f"Device assistant failed: {exc}"}), 500
