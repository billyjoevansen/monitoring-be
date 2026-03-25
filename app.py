import os
import logging
from flask import Flask
from flask_cors import CORS
from routes.train import train_bp
from routes.predict import predict_bp
from routes.reconcile import reconcile_bp
from routes.config import config_bp
from routes.archive import archive_bp
from routes.visualize import visualize_bp
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)


def create_app():
    app = Flask(__name__)

    raw_origins = os.getenv(
        'CORS_ORIGINS',
        'http://localhost:3000',
        'http://127.0.0.1:3000'
    )

    # CORS — read origins from environment
    allowed_origins = [
        origin.strip()
        for origin in raw_origins.split(',')
        if origin.strip()
    ]
    CORS(app, resources={
        r"/api/*": {
            "origins": [origin.strip() for origin in allowed_origins],
            "methods": ["GET", "POST", "PUT", "DELETE"],
            "allow_headers": ["Content-Type", "Authorization"],
        }
    })

    # Konfigurasi upload
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # Max 50MB

    # Register Blueprints
    app.register_blueprint(train_bp)
    app.register_blueprint(predict_bp)
    app.register_blueprint(reconcile_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(archive_bp)
    app.register_blueprint(visualize_bp)

    # Health check
    @app.route('/api/health', methods=['GET'])
    def health():
        return {'status': 'ok', 'message': 'Pupuk Subsidi Monitoring API is running'}, 200

    return app


if __name__ == '__main__':
    app = create_app()
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug, host='0.0.0.0', port=5000)