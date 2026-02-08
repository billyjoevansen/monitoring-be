from flask import Blueprint, request, jsonify
from config.model_config import (
    load_config,
    save_config,
    validate_config,
    DEFAULT_CONFIG,
    PARAM_RULES,
)

config_bp = Blueprint('config', __name__)


@config_bp.route('/api/config', methods=['GET'])
def get_config():
    """
    Mendapatkan konfigurasi model saat ini.
    Frontend bisa menampilkan ini di form setting.
    """
    config = load_config()

    # Tambahkan info parameter rules untuk frontend
    param_info = {}
    for param, rules in PARAM_RULES.items():
        info = {}
        if 'min' in rules:
            info['min'] = rules['min']
        if 'max' in rules:
            info['max'] = rules['max']
        if 'choices' in rules:
            info['choices'] = rules['choices']
        if 'choices_str' in rules:
            info['choices'] = rules['choices_str']
        param_info[param] = info

    return jsonify({
        'config': config,
        'param_rules': param_info,
        'message': 'Konfigurasi model saat ini.',
    }), 200


@config_bp.route('/api/config', methods=['PUT'])
def update_config():
    """
    Mengubah konfigurasi model dari frontend.
    Setelah diubah, user perlu train ulang agar perubahan berlaku.

    Body JSON:
    {
        "hyperparameters": { ... },
        "training_config": { ... }
    }
    """
    try:
        new_config = request.get_json()

        if not new_config:
            return jsonify({'error': 'Body JSON tidak boleh kosong.'}), 400

        # Validasi
        errors = validate_config(new_config)
        if errors:
            return jsonify({
                'error': 'Konfigurasi tidak valid.',
                'details': errors,
            }), 400

        # Merge dengan config yang ada (partial update)
        current_config = load_config()

        if 'hyperparameters' in new_config:
            current_config['hyperparameters'].update(new_config['hyperparameters'])
        if 'training_config' in new_config:
            current_config['training_config'].update(new_config['training_config'])

        # Simpan
        save_config(current_config)

        return jsonify({
            'config': current_config,
            'message': 'Konfigurasi berhasil diperbarui. Silakan train ulang model agar perubahan berlaku.',
        }), 200

    except Exception as e:
        return jsonify({'error': f'Terjadi kesalahan: {str(e)}'}), 500


@config_bp.route('/api/config/reset', methods=['POST'])
def reset_config():
    """
    Reset konfigurasi ke default.
    """
    save_config(DEFAULT_CONFIG)

    return jsonify({
        'config': DEFAULT_CONFIG,
        'message': 'Konfigurasi berhasil direset ke default. Silakan train ulang model.',
    }), 200