from flask import Blueprint, request, jsonify
from services.model_services import ModelService

classify_bp = Blueprint('classify', __name__)


@classify_bp.route('/api/classify', methods=['POST'])
def classify():
    """
    Klasifikasi data dari arsip rekonsiliasi.
    Input: JSON data rekonsiliasi (bukan 2 file).
    """
    try:
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


@classify_bp.route('/api/model/info', methods=['GET'])
def model_info():
    """
    Cek info model yang sudah dilatih.
    """
    try:
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