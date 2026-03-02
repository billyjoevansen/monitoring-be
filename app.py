from flask import Flask
from flask_cors import CORS
from routes.train import train_bp
from routes.predict import predict_bp
from routes.predict_routes import classify_bp
from routes.reconcile import reconcile_bp
from routes.config import config_bp
from routes.archive import archive_bp
from routes.visualize import visualize_bp


def create_app():
    app = Flask(__name__)

    # CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
            "methods": ["GET", "POST", "PUT"],
            "allow_headers": ["Content-Type"],
        }
    })

    # Konfigurasi upload
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # Max 50MB

    # Register Blueprints
    app.register_blueprint(train_bp)
    app.register_blueprint(predict_bp)
    app.register_blueprint(classify_bp)
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
    app.run(debug=True, host='0.0.0.0', port=5000)