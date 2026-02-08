from flask import Blueprint, request, jsonify
from utils.file_handler import parse_excel, standardize_rdkk, standardize_siverval
from services.preprocessing import merge_data, engineer_features
from services.prediction import predict

predict_bp = Blueprint('predict', __name__)


@predict_bp.route('/api/predict', methods=['POST'])
def predict_route():
    """
    Endpoint untuk melakukan prediksi pada data baru.
    Hanya memproses dan mengembalikan hasil.
    Penyimpanan ke database dilakukan terpisah via /api/archive/save.
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

        # --- Prediksi ---
        result_df = predict(featured_df)

        # --- Format Response ---
        total = len(result_df)
        normal = (result_df['prediksi'] == 0).sum()
        tidak_normal = (result_df['prediksi'] == 1).sum()

        summary = {
            'total_petani': int(total),
            'normal': int(normal),
            'tidak_normal': int(tidak_normal),
            'persentase_normal': round(normal / total * 100, 2) if total > 0 else 0,
            'persentase_tidak_normal': round(tidak_normal / total * 100, 2) if total > 0 else 0,
        }

        detail = []
        for _, row in result_df.iterrows():
            petani = {
                'nama_petani': str(row.get('nama_petani', '')),
                'nik': str(row.get('nik', '')),
                'poktan': str(row.get('poktan', '')),
                'alamat': str(row.get('alamat', '')),
                'status': row.get('prediksi_label', ''),
                'confidence': row.get('confidence', 0),
                'kios_rdkk': str(row.get('nama_kios_rdkk', '')),
                'kios_siverval': str(row.get('nama_kios_siverval', '')),
                'kios_sesuai': bool(row.get('kios_sesuai', True)),
                'pupuk': {
                    'urea': {
                        'diajukan': float(row.get('urea_diajukan', 0)),
                        'ditebus': float(row.get('urea_tebus', 0)),
                        'rasio': round(float(row.get('rasio_tebus_urea', 0)), 2),
                    },
                    'npk': {
                        'diajukan': float(row.get('npk_diajukan', 0)),
                        'ditebus': float(row.get('npk_tebus', 0)),
                        'rasio': round(float(row.get('rasio_tebus_npk', 0)), 2),
                    },
                    'za': {
                        'diajukan': float(row.get('za_diajukan', 0)),
                        'ditebus': float(row.get('za_tebus', 0)),
                        'rasio': round(float(row.get('rasio_tebus_za', 0)), 2),
                    },
                    'npk_formula': {
                        'diajukan': float(row.get('npk_formula_diajukan', 0)),
                        'ditebus': float(row.get('npk_formula_tebus', 0)),
                        'rasio': round(float(row.get('rasio_tebus_npk_formula', 0)), 2),
                    },
                    'organik': {
                        'diajukan': float(row.get('organik_diajukan', 0)),
                        'ditebus': float(row.get('organik_tebus', 0)),
                        'rasio': round(float(row.get('rasio_tebus_organik', 0)), 2),
                    },
                },
                'total_luas_lahan': float(row.get('total_luas_lahan', 0)),
                'total_pupuk_diajukan': float(row.get('total_pupuk_diajukan', 0)),
                'total_pupuk_ditebus': float(row.get('total_pupuk_ditebus', 0)),
                'selisih_total_pupuk': float(row.get('selisih_total_pupuk', 0)),
            }
            detail.append(petani)

        return jsonify({
            'summary': summary,
            'detail': detail,
        }), 200

    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Terjadi kesalahan: {str(e)}'}), 500