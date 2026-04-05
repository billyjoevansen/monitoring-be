from flask import Blueprint, request, jsonify
from services.database import save_reconciliation, save_prediction

archive_bp = Blueprint('archive', __name__)


@archive_bp.route('/api/archive/save', methods=['POST'])
def save_archive():
    """
    Endpoint untuk menyimpan hasil ke Supabase.
    Dipanggil dari frontend saat user klik tombol SIMPAN atau CETAK.

    Body JSON:
    {
        "type": "reconcile" | "predict",
        "filename_rdkk": "data_rdkk.xlsx",
        "filename_siverval": "data_siverval.xlsx",
        "summary": { ... },
        "detail": [ ... ]
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Body JSON tidak boleh kosong.'}), 400

        # Validasi field wajib
        required_fields = ['type', 'summary', 'detail']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Field "{field}" wajib diisi.'}), 400

        archive_type = data['type']
        summary = data['summary']
        detail = data['detail']
        filename_rdkk = data.get('filename_rdkk', 'unknown')
        filename_siverval = data.get('filename_siverval', 'unknown')

        # Konsisten: siapkan model_info untuk response
        model_info = {}

        # Simpan berdasarkan tipe
        if archive_type == 'reconcile':
            result = save_reconciliation(
                summary=summary,
                detail=detail,
                filename_rdkk=filename_rdkk,
                filename_siverval=filename_siverval,
            )
        elif archive_type == 'predict':
            # Ambil model metrics dari .pkl saat menyimpan arsip
            try:
                from services.prediction import load_model
                md = load_model()
                model_info = md.get('metrics', {}) or {}
            except Exception:
                model_info = {}  # Model belum ditraining atau pkl lama

            result = save_prediction(
                summary=summary,
                detail=detail,
                filename_rdkk=filename_rdkk,
                filename_siverval=filename_siverval,
                model_info=model_info,
            )
        else:
            return jsonify({
                'error': f'Tipe arsip tidak valid: "{archive_type}". Gunakan "reconcile" atau "predict".'
            }), 400

        response_payload = {
            'message': 'Data berhasil disimpan ke arsip.',
            'session_id': result['session_id'],
            'total_saved': result['total_saved'],
        }

        # Hanya predict yang mengembalikan model_info
        if archive_type == 'predict':
            response_payload['model_info'] = model_info

        return jsonify(response_payload), 200

    except Exception as e:
        return jsonify({'error': f'Gagal menyimpan arsip: {str(e)}'}), 500


@archive_bp.route('/api/archive/history', methods=['GET'])
def get_history():
    """
    Endpoint untuk melihat riwayat arsip.
    Digunakan di halaman riwayat/history di frontend.

    Query params:
    - type: "reconcile" | "predict" (wajib)
    - limit: jumlah data (default 10)
    """
    try:
        from config.supabase_client import get_supabase

        archive_type = request.args.get('type')
        limit = int(request.args.get('limit', 10))

        if not archive_type:
            return jsonify({'error': 'Parameter "type" wajib diisi.'}), 400

        supabase = get_supabase()

        if archive_type == 'reconcile':
            result = supabase.table('rekonsiliasi_sessions') \
                .select('*') \
                .order('created_at', desc=True) \
                .limit(limit) \
                .execute()
        elif archive_type == 'predict':
            result = supabase.table('prediksi_sessions') \
                .select('*') \
                .order('created_at', desc=True) \
                .limit(limit) \
                .execute()
        else:
            return jsonify({'error': 'Tipe harus "reconcile" atau "predict".'}), 400

        return jsonify({
            'type': archive_type,
            'total': len(result.data),
            'data': result.data,
        }), 200

    except Exception as e:
        return jsonify({'error': f'Gagal mengambil riwayat: {str(e)}'}), 500


@archive_bp.route('/api/archive/<int:session_id>', methods=['GET'])
def get_archive_detail(session_id):
    """
    Endpoint untuk melihat detail arsip berdasarkan session_id.

    Query params:
    - type: "reconcile" | "predict" (wajib)
    """
    try:
        from config.supabase_client import get_supabase

        archive_type = request.args.get('type')

        if not archive_type:
            return jsonify({'error': 'Parameter "type" wajib diisi.'}), 400

        supabase = get_supabase()

        if archive_type == 'reconcile':
            session = supabase.table('rekonsiliasi_sessions') \
                .select('*') \
                .eq('id', session_id) \
                .execute()
            detail = supabase.table('rekonsiliasi_detail') \
                .select('*') \
                .eq('session_id', session_id) \
                .execute()
        elif archive_type == 'predict':
            session = supabase.table('prediksi_sessions') \
                .select('*') \
                .eq('id', session_id) \
                .execute()
            detail = supabase.table('prediksi_detail') \
                .select('*') \
                .eq('session_id', session_id) \
                .execute()
        else:
            return jsonify({'error': 'Tipe harus "reconcile" atau "predict".'}), 400

        if not session.data:
            return jsonify({'error': f'Session ID {session_id} tidak ditemukan.'}), 404

        return jsonify({
            'session': session.data[0],
            'detail': detail.data,
            'total_detail': len(detail.data),
        }), 200

    except Exception as e:
        return jsonify({'error': f'Gagal mengambil detail arsip: {str(e)}'}), 500