from flask import Blueprint, request, jsonify
from utils.file_handler import parse_excel, standardize_rdkk, standardize_siverval
from services.preprocessing import merge_data, engineer_features
from services.prediction import predict, load_model

predict_bp = Blueprint('predict', __name__)


@predict_bp.route('/api/predict', methods=['POST'])
def predict_route():
    """
    Endpoint prediksi dari 2 file (legacy).
    """
    try:
        if 'rdkk' not in request.files:
            return jsonify({'error': 'File RDKK tidak ditemukan.'}), 400
        if 'siverval' not in request.files:
            return jsonify({'error': 'File SIVERVAL tidak ditemukan.'}), 400

        rdkk_file = request.files['rdkk']
        siverval_file = request.files['siverval']

        if rdkk_file.filename == '' or siverval_file.filename == '':
            return jsonify({'error': 'Nama file tidak boleh kosong.'}), 400

        rdkk_df = parse_excel(rdkk_file, header_row=0)
        siverval_df = parse_excel(siverval_file, header_row=1)

        rdkk_df = standardize_rdkk(rdkk_df)
        siverval_df = standardize_siverval(siverval_df)

        merged_df = merge_data(rdkk_df, siverval_df)
        featured_df = engineer_features(merged_df)

        result_df = predict(featured_df)

        total = len(result_df)
        normal = int((result_df['prediksi'] == 0).sum())
        tidak_normal = int((result_df['prediksi'] == 1).sum())

        summary = {
            'total_petani': total,
            'normal': normal,
            'tidak_normal': tidak_normal,
            'persentase_normal': round(normal / total * 100, 2) if total > 0 else 0,
            'persentase_tidak_normal': round(tidak_normal / total * 100, 2) if total > 0 else 0,
        }

        detail = []
        for _, row in result_df.iterrows():
            petani = {
                'nama_petani': str(row.get('nama_petani', '')),
                'nik': str(row.get('nik', '')),
                'poktan': str(row.get('poktan', '')),
                'status': row.get('prediksi_label', ''),
                'confidence': round(float(row.get('confidence', 0)), 4),
                'kios_sesuai': bool(row.get('kios_sesuai', True)),
                'total_pupuk_diajukan_kg': float(row.get('total_pupuk_diajukan', 0)),
                'total_pupuk_ditebus_kg': float(row.get('total_pupuk_ditebus', 0)),
                'selisih_total_kg': float(row.get('selisih_total', 0)),
            }
            detail.append(petani)

        return jsonify({'summary': summary, 'detail': detail}), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Terjadi kesalahan: {str(e)}'}), 500


@predict_bp.route('/api/classify', methods=['POST'])
def classify_route():
    """
    Klasifikasi data dari arsip rekonsiliasi (1 input JSON).
    """
    try:
        import pandas as pd
        import numpy as np

        data = request.get_json()

        if not data or 'detail' not in data:
            return jsonify({'error': 'Data rekonsiliasi diperlukan.'}), 400

        detail = data['detail']

        if not detail or len(detail) == 0:
            return jsonify({'error': 'Data detail kosong.'}), 400

        # Load model (dict berisi 'model' dan 'features')
        model_data = load_model()
        model = model_data['model']
        features = model_data['features']

        df = pd.DataFrame(detail)

        # Mapping kolom arsip → feature columns
        col_mapping = {
            'total_pupuk_diajukan_kg': ['total_pupuk_diajukan_kg', 'total_pupuk_diajukan'],
            'total_pupuk_ditebus_kg': ['total_pupuk_ditebus_kg', 'total_pupuk_ditebus'],
            'selisih_total_kg': ['selisih_total_kg', 'selisih_total'],
        }

        for target, sources in col_mapping.items():
            if target not in df.columns:
                for src in sources:
                    if src in df.columns:
                        df[target] = df[src]
                        break
                else:
                    df[target] = 0

        # Numerik
        numeric_cols = ['total_pupuk_diajukan_kg', 'total_pupuk_ditebus_kg', 'selisih_total_kg']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # kios_sesuai → numerik
        if 'kios_sesuai' in df.columns:
            df['kios_sesuai_num'] = df['kios_sesuai'].apply(
                lambda x: 1 if x in [True, 'true', 'True', 'Ya', 'ya', 1, '1'] else 0
            )
        else:
            df['kios_sesuai_num'] = 0

        # Rename untuk matching feature columns
        if 'kios_sesuai' in features and 'kios_sesuai_num' in df.columns:
            df['kios_sesuai'] = df['kios_sesuai_num']

        # Pastikan semua feature ada
        for col in features:
            if col not in df.columns:
                df[col] = 0

        X = df[features].fillna(0)

        predictions = model.predict(X)
        probabilities = model.predict_proba(X)
        confidence = np.max(probabilities, axis=1)

        # Build result
        result_detail = []
        for i in range(len(df)):
            original = detail[i] if i < len(detail) else {}
            result_detail.append({
                'nama_petani': str(original.get('nama_petani', '')),
                'nik': str(original.get('nik', '')),
                'poktan': str(original.get('poktan', '')),
                'kios_sesuai': original.get('kios_sesuai', False),
                'total_pupuk_diajukan_kg': float(df.iloc[i].get('total_pupuk_diajukan_kg', 0)),
                'total_pupuk_ditebus_kg': float(df.iloc[i].get('total_pupuk_ditebus_kg', 0)),
                'selisih_total_kg': float(df.iloc[i].get('selisih_total_kg', 0)),
                'status': 'NORMAL' if predictions[i] == 0 else 'TIDAK NORMAL',
                'confidence': round(float(confidence[i]), 4),
            })

        normal_count = int((predictions == 0).sum())
        tidak_normal_count = int((predictions == 1).sum())
        total = len(predictions)

        return jsonify({
            'summary': {
                'total_petani': total,
                'normal': normal_count,
                'tidak_normal': tidak_normal_count,
                'persentase_normal': round(normal_count / total * 100, 2) if total > 0 else 0,
                'persentase_tidak_normal': round(tidak_normal_count / total * 100, 2) if total > 0 else 0,
            },
            'detail': result_detail,
        }), 200

    except FileNotFoundError:
        return jsonify({
            'error': 'Model belum dilatih. Lakukan training terlebih dahulu.'
        }), 404
    except Exception as e:
        return jsonify({'error': f'Terjadi kesalahan: {str(e)}'}), 500


@predict_bp.route('/api/model/info', methods=['GET'])
def model_info():
    """Cek info model yang sudah dilatih."""
    try:
        import os

        MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')
        MODEL_PATH = os.path.join(MODEL_DIR, 'random_forest.pkl')

        if not os.path.exists(MODEL_PATH):
            return jsonify({'error': 'Model belum dilatih.', 'trained': False}), 404

        model_data = load_model()
        model = model_data['model']
        features = model_data['features']
        model_size = os.path.getsize(MODEL_PATH) / 1024

        return jsonify({
            'trained': True,
            'n_estimators': model.n_estimators,
            'n_features': model.n_features_in_,
            'features': features,
            'classes': model.classes_.tolist(),
            'size_kb': round(model_size, 1),
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500