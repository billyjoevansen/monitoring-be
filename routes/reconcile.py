from flask import Blueprint, request, jsonify
from utils.file_handler import parse_excel, standardize_rdkk, standardize_siverval
from services.preprocessing import merge_data, engineer_features
from services.reconciliation import reconcile

reconcile_bp = Blueprint('reconcile', __name__)


@reconcile_bp.route('/api/reconcile', methods=['POST'])
def reconcile_route():
    """
    Endpoint untuk rekonsiliasi data RDKK vs SIVERVAL.
    Hanya memproses dan mengembalikan hasil.
    Penyimpanan ke database dilakukan via /api/archive/save.
    """
    try:
        if 'rdkk' not in request.files:
            return jsonify({'error': 'File RDKK tidak ditemukan. Kirim dengan key "rdkk".'}), 400
        if 'siverval' not in request.files:
            return jsonify({'error': 'File SIVERVAL tidak ditemukan. Kirim dengan key "siverval".'}), 400

        rdkk_file = request.files['rdkk']
        siverval_file = request.files['siverval']

        if rdkk_file.filename == '' or siverval_file.filename == '':
            return jsonify({'error': 'Nama file tidak boleh kosong.'}), 400

        # --- Parse & Standarisasi ---
        rdkk_df = parse_excel(rdkk_file, header_row=0)
        siverval_df = parse_excel(siverval_file, header_row=1)

        rdkk_df = standardize_rdkk(rdkk_df)
        siverval_df = standardize_siverval(siverval_df)

        # --- Preprocessing ---
        merged_df = merge_data(rdkk_df, siverval_df)
        featured_df = engineer_features(merged_df)

        # --- Rekonsiliasi ---
        result = reconcile(featured_df)

        return jsonify(result), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Terjadi kesalahan: {str(e)}'}), 500