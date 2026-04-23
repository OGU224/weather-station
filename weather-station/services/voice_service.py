"""Service vocal — TTS / STT / LLM.
- text_to_speech(text) -> bytes audio (Google Cloud TTS)
- speech_to_text(audio) -> texte (Google Cloud STT)
- generate_response(question, context) -> reponse LLM (OpenAI/Gemini)
- build_context_prompt(sensor_data, weather_data, history) -> prompt pour le LLM
"""
