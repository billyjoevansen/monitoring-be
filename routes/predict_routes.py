from flask import Blueprint, request, jsonify
import numpy as np

predict_bp = Blueprint('predict', __name__)


@predict_bp.route('/api/classify', methods=['POST'])
def classify():
    """
    Klasifikasi data dari arsip rekonsiliasi.
    Input: JSON data rekonsiliasi (bukan 2 file).
    """
    try:
        from app.services.model_service import ModelService

        data = request.get_json()

        if not data or 'detail' not in data:
            return jsonify({'error': 'Data rekonsiliasi diperlukan.'}), 400

        detail = data['detail']

        if not detail or len(detail) == 0:
            return jsonify({'error': 'Data detail kosong.'}), 400

        model_service = ModelService()
        result = model_service.classify(detail)

        return jsonify(result), 200

    except FileNotFoundError:
        return jsonify({
            'error': 'Model belum dilatih. Lakukan training terlebih dahulu.'
        }), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@predict_bp.route('/api/train', methods=['POST'])
def train():
    """
    Training model Random Forest.
    Input: JSON data dummy atau data rekonsiliasi untuk training.
    """
    try:
        from app.services.model_service import ModelService

        model_service = ModelService()
        result = model_service.train_with_dummy()

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@predict_bp.route('/api/model/info', methods=['GET'])
def model_info():
    """
    Cek info model yang sudah dilatih.
    """
    try:
        from app.services.model_service import ModelService

        model_service = ModelService()
        info = model_service.get_model_info()

        return jsonify(info), 200

    except FileNotFoundError:
        return jsonify({
            'error': 'Model belum dilatih.',
            'trained': False
        }), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500