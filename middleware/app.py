import os
import sys
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Import blueprints
from middleware.routes.sensor_routes import sensor_bp
from middleware.routes.weather_routes import weather_bp
from middleware.routes.voice_routes import voice_bp
from middleware.routes.music_routes import music_bp

def create_app():
    load_dotenv()
    app = Flask(__name__)
    CORS(app)
    
    # Register blueprints
    app.register_blueprint(sensor_bp, url_prefix='/api/sensors')
    app.register_blueprint(weather_bp, url_prefix='/api/weather')
    app.register_blueprint(voice_bp, url_prefix='/api/voice')
    app.register_blueprint(music_bp, url_prefix='/api/music')
    
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({"status": "ok", "message": "Weather Station API is running!"}), 200
        
    return app

if __name__ == '__main__':
    app = create_app()
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", 5000))
    app.run(host=host, port=port, debug=True)
