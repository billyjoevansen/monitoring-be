from flask import Blueprint, request, jsonify
from utils.file_handler import parse_excel, standardize_rdkk, standardize_siverval
from services.preprocessing import merge_data, engineer_features
from services.labeling import assign_labels, get_label_summary
from services.prediction import train_model

train_bp = Blueprint('train', __name__)


@train_bp.route('/api/train', methods=['POST'])
def train():
    """
    Endpoint untuk melatih model Random Forest.

    Input: 2 file Excel (rdkk dan siverval) via form-data
    Output: Metrik evaluasi model (accuracy, f1, confusion matrix, dll)
    """
    try:
        # --- Validasi file upload ---
        if 'rdkk' not in request.files:
            return jsonify({'error': 'File RDKK tidak ditemukan. Kirim dengan key "rdkk".'}), 400
        if 'siverval' not in request.files:
            return jsonify({'error': 'File SIVERVAL tidak ditemukan. Kirim dengan key "siverval".'}), 400

        rdkk_file = request.files['rdkk']
        siverval_file = request.files['siverval']

        if rdkk_file.filename == '' or siverval_file.filename == '':
            return jsonify({'error': 'Nama file tidak boleh kosong.'}), 400

        # --- Parse & Standarisasi ---
        rdkk_df = parse_excel(rdkk_file, header_row=0)           # RDKK header di baris 1
        siverval_df = parse_excel(siverval_file, header_row=1)    # SIVERVAL header di baris 2 (1-indexed)

        rdkk_df = standardize_rdkk(rdkk_df)
        siverval_df = standardize_siverval(siverval_df)

        # --- Preprocessing: Merge & Feature Engineering ---
        merged_df = merge_data(rdkk_df, siverval_df)
        featured_df = engineer_features(merged_df)

        # --- Labeling ---
        labeled_df = assign_labels(featured_df)
        label_summary = get_label_summary(labeled_df)

        # --- Training ---
        result = train_model(labeled_df)
        result['label_distribution'] = label_summary

        return jsonify(result), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Terjadi kesalahan: {str(e)}'}), 500