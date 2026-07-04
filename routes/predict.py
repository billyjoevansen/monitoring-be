import os
from datetime import datetime
from flask import Blueprint, request, jsonify
from utils.file_handler import parse_excel, standardize_rdkk, standardize_siverval
from services.preprocessing import merge_data, engineer_features
from services.prediction import predict, load_model, MODEL_PATH

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
                'total_pupuk_diajukan_kg': float(row.get('total_pupuk_diajukan', 0)),
                'total_pupuk_ditebus_kg': float(row.get('total_pupuk_ditebus', 0)),
                'selisih_total_kg': float(row.get('selisih_total_pupuk', 0)),
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

    Menerima output dari /api/reconcile (field 'detail') dan
    merekonstruksi semua fitur model dari data pupuk per jenis
    yang sudah tersedia di struktur rekonsiliasi.
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

        model_data = load_model()
        model    = model_data['model']
        features = model_data['features']

        # =====================================================
        # REKONSTRUKSI FITUR DARI DETAIL REKONSILIASI
        # Struktur tiap petani di detail:
        #   total_pupuk_diajukan_kg, total_pupuk_ditebus_kg,
        #   total_luas_lahan_ha,
        #   pupuk: { urea: {diajukan_kg, ditebus_kg}, npk: ..., dst }
        # =====================================================
        rows = []
        for petani in detail:
            pupuk  = petani.get('pupuk', {})
            total_diajukan = float(petani.get('total_pupuk_diajukan_kg', 0))
            total_ditebus  = float(petani.get('total_pupuk_ditebus_kg', 0))
            luas_lahan     = float(petani.get('total_luas_lahan_ha', 0))

            # Pupuk per jenis
            urea_aj  = float(pupuk.get('urea',        {}).get('diajukan_kg', 0))
            npk_aj   = float(pupuk.get('npk',         {}).get('diajukan_kg', 0))
            za_aj    = float(pupuk.get('za',          {}).get('diajukan_kg', 0))
            organik_aj = float(pupuk.get('organik',    {}).get('diajukan_kg', 0))

            urea_tb  = float(pupuk.get('urea',        {}).get('ditebus_kg', 0))
            npk_tb   = float(pupuk.get('npk',         {}).get('ditebus_kg', 0))
            za_tb    = float(pupuk.get('za',          {}).get('ditebus_kg', 0))
            organik_tb = float(pupuk.get('organik',    {}).get('ditebus_kg', 0))
            sp36_tb  = float(pupuk.get('sp36',        {}).get('ditebus_kg', 0))
            organik_cair_tb = float(pupuk.get('organik_cair', {}).get('ditebus_kg', 0))

            # Proporsi pengajuan (hanya Urea & NPK)
            proporsi_urea    = urea_aj  / total_diajukan if total_diajukan > 0 else 0
            proporsi_npk     = npk_aj   / total_diajukan if total_diajukan > 0 else 0

            # Proporsi penebusan (hanya Urea & NPK)
            prop_tb_urea  = urea_tb  / total_ditebus if total_ditebus > 0 else 0
            prop_tb_npk   = npk_tb   / total_ditebus if total_ditebus > 0 else 0

            # Intensitas per hektar
            urea_per_ha = urea_aj / luas_lahan if luas_lahan > 0 else 0
            npk_per_ha = npk_aj / luas_lahan if luas_lahan > 0 else 0
            total_pupuk_per_ha = total_diajukan / luas_lahan if luas_lahan > 0 else 0

            # Rata-rata pupuk per MT
            jumlah_mt = int(petani.get('jumlah_mt_aktif', 0))
            rata_pupuk_per_mt = total_diajukan / jumlah_mt if jumlah_mt > 0 else 0

            # Flag melebihi kuota (dari reconcile detail)
            flag_melebihi = int(petani.get('flag_melebihi_kuota', 0))

            # Rasio total penebusan
            rasio_total_penebusan = total_ditebus / total_diajukan if total_diajukan > 0 else 0.0

            # Selisih total pupuk
            selisih_total_pupuk = total_diajukan - total_ditebus

            # Selisih per jenis pupuk
            selisih_urea = urea_aj - urea_tb
            selisih_npk  = npk_aj - npk_tb
            selisih_za   = za_aj - za_tb
            selisih_organik = organik_aj - organik_tb

            # Frekuensi transaksi (dari reconcile detail)
            frekuensi = int(petani.get('frekuensi_transaksi', 0))

            # Tebus di luar RDKK (SP36 / Organik Cair)
            tebus_diluar_rdkk = 1 if (sp36_tb > 0 or organik_cair_tb > 0) else 0

            # Hitung jumlah jenis pupuk yang diajukan & ditebus (dari 5 jenis)
            jenis_diajukan = sum(1 for k in ['urea','npk','za','npk_formula','organik']
                               if float(pupuk.get(k, {}).get('diajukan_kg', 0)) > 0)
            jenis_ditebus = sum(1 for k in ['urea','npk','za','npk_formula','organik']
                              if float(pupuk.get(k, {}).get('ditebus_kg', 0)) > 0)

            rows.append({
                'total_pupuk_diajukan':        total_diajukan,
                'total_pupuk_ditebus':         total_ditebus,
                'urea_per_ha':                 urea_per_ha,
                'npk_per_ha':                  npk_per_ha,
                'total_pupuk_per_ha':          total_pupuk_per_ha,
                'proporsi_urea':               proporsi_urea,
                'proporsi_npk':                proporsi_npk,
                'proporsi_tebus_urea':         prop_tb_urea,
                'proporsi_tebus_npk':          prop_tb_npk,
                'selisih_urea':                selisih_urea,
                'selisih_npk':                 selisih_npk,
                'selisih_za':                  selisih_za,
                'selisih_organik':             selisih_organik,
                'jenis_pupuk_ditebus':         jenis_ditebus,
                'selisih_jenis_pupuk':         jenis_diajukan - jenis_ditebus,
                'total_luas_lahan':            luas_lahan,
                'jumlah_mt_aktif':             jumlah_mt,
                'ada_penebusan':               1 if total_ditebus > 0 else 0,
                'rata_pupuk_per_mt':           rata_pupuk_per_mt,
                'rasio_total_penebusan':       rasio_total_penebusan,
                'selisih_total_pupuk':         selisih_total_pupuk,
                'frekuensi_transaksi':         frekuensi,
                'flag_melebihi_kuota':         flag_melebihi,
                'tebus_diluar_rdkk':           tebus_diluar_rdkk,
            })

        df = pd.DataFrame(rows)

        # Pastikan semua feature ada (fallback 0 jika model diretrain dengan fitur baru)
        for col in features:
            if col not in df.columns:
                df[col] = 0

        X = df[features].fillna(0)

        predictions   = model.predict(X)
        probabilities = model.predict_proba(X)
        confidence    = np.max(probabilities, axis=1)

        result_detail = []
        for i in range(len(df)):
            original = detail[i] if i < len(detail) else {}
            result_detail.append({
                'nama_petani':            str(original.get('nama_petani', '')),
                'nik':                    str(original.get('nik', '')),
                'poktan':                 str(original.get('poktan', '')),
                'total_pupuk_diajukan_kg': float(df.iloc[i]['total_pupuk_diajukan']),
                'total_pupuk_ditebus_kg':  float(df.iloc[i]['total_pupuk_ditebus']),
                'selisih_total_kg':        float(original.get('selisih_total_kg', 0)),
                'status':                 'NORMAL' if predictions[i] == 0 else 'TIDAK NORMAL',
                'confidence':             round(float(confidence[i]), 4),
            })

        normal_count      = int((predictions == 0).sum())
        tidak_normal_count = int((predictions == 1).sum())
        total             = len(predictions)

        model_info = model_data.get('metrics', {}) or {}

        return jsonify({
            'summary': {
                'total_petani': total,
                'normal': normal_count,
                'tidak_normal': tidak_normal_count,
                'persentase_normal': round(normal_count / total * 100, 2) if total > 0 else 0,
                'persentase_tidak_normal': round(tidak_normal_count / total * 100, 2) if total > 0 else 0,
            },
            'detail': result_detail,
            'model_info': model_info,
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
        if not os.path.exists(MODEL_PATH):
            return jsonify({'error': 'Model belum dilatih.', 'trained': False}), 404

        # Info file
        stat = os.stat(MODEL_PATH)
        size_kb       = round(stat.st_size / 1024, 2)
        last_modified = datetime.fromtimestamp(stat.st_mtime).isoformat()

        # Info dari dalam .pkl
        model_data = load_model()
        model    = model_data['model']
        features = model_data['features']
        params   = model_data.get('params', {})

        # Baca metrik dari pkl (disimpan saat training)
        metrics    = model_data.get('metrics', {})
        trained_at = model_data.get('trained_at', last_modified)

        return jsonify({
            'trained':       True,
            'trained_at':    trained_at,
            'last_modified': last_modified,
            'size_kb':       size_kb,
            'model_info': {
                'accuracy':          metrics.get('accuracy'),
                'f1_score_weighted': metrics.get('f1_score_weighted'),
                'oob_score':         metrics.get('oob_score'),
                'algorithm':         'RandomForestClassifier',
                'total_features':    len(features),
                'features':          features,
                'hyperparameters': {
                    'n_estimators':      params.get('n_estimators'),
                    'criterion':         params.get('criterion'),
                    'max_depth':         params.get('max_depth'),
                    'max_features':      params.get('max_features'),
                    'min_samples_split': params.get('min_samples_split'),
                    'min_samples_leaf':  params.get('min_samples_leaf'),
                    'class_weight':      params.get('class_weight'),
                    'oob_score':         params.get('oob_score'),
                },
            },
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500