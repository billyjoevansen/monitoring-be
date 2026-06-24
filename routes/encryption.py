from flask import Blueprint, request, jsonify
from services.encryption import encrypt_nik, decrypt_nik

encryption_bp = Blueprint('encryption', __name__)


@encryption_bp.route('/api/encrypt-nik', methods=['POST'])
def api_encrypt_nik():
    """
    Encrypt NIK dalam array detail objects.

    Body JSON:
    {
        "detail": [
            { "nik": "3201234567890001", "nama_petani": "...", ... },
            ...
        ]
    }
    """
    try:
        data = request.get_json(silent=True)

        if not data or 'detail' not in data:
            return jsonify({'error': 'Field "detail" diperlukan.'}), 400

        detail = data['detail']

        if not isinstance(detail, list):
            return jsonify({'error': '"detail" harus berupa array.'}), 400

        encrypted_detail = []
        for row in detail:
            encrypted_row = {**row}

            # Handle both 'nik' and 'NIK' field variations
            if 'nik' in encrypted_row and isinstance(encrypted_row['nik'], str) and encrypted_row['nik']:
                encrypted_row['nik'] = encrypt_nik(encrypted_row['nik'])
            if 'NIK' in encrypted_row and isinstance(encrypted_row['NIK'], str) and encrypted_row['NIK']:
                encrypted_row['NIK'] = encrypt_nik(encrypted_row['NIK'])

            encrypted_detail.append(encrypted_row)

        return jsonify({'detail': encrypted_detail}), 200

    except Exception as e:
        return jsonify({'error': f'Gagal encrypt NIK: {str(e)}'}), 500


@encryption_bp.route('/api/decrypt-nik', methods=['POST'])
def api_decrypt_nik():
    """
    Decrypt NIK dalam array detail objects.

    Body JSON:
    {
        "detail": [
            { "nik": "base64_encrypted_string", "nama_petani": "...", ... },
            ...
        ]
    }
    """
    try:
        data = request.get_json(silent=True)

        if not data or 'detail' not in data:
            return jsonify({'error': 'Field "detail" diperlukan.'}), 400

        detail = data['detail']

        if not isinstance(detail, list):
            return jsonify({'error': '"detail" harus berupa array.'}), 400

        decrypted_detail = []
        for row in detail:
            decrypted_row = {**row}

            # Handle both 'nik' and 'NIK' field variations
            if 'nik' in decrypted_row and isinstance(decrypted_row['nik'], str) and decrypted_row['nik']:
                decrypted_row['nik'] = decrypt_nik(decrypted_row['nik'])
            if 'NIK' in decrypted_row and isinstance(decrypted_row['NIK'], str) and decrypted_row['NIK']:
                decrypted_row['NIK'] = decrypt_nik(decrypted_row['NIK'])

            decrypted_detail.append(decrypted_row)

        return jsonify({'detail': decrypted_detail}), 200

    except Exception as e:
        return jsonify({'error': f'Gagal decrypt NIK: {str(e)}'}), 500
