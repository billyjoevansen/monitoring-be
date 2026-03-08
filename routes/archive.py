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

        # Simpan berdasarkan tipe
        if archive_type == 'reconcile':
            result = save_reconciliation(
                summary=summary,
                detail=detail,
                filename_rdkk=filename_rdkk,
                filename_siverval=filename_siverval,
            )
        elif archive_type == 'predict':
            result = save_prediction(
                summary=summary,
                detail=detail,
                filename_rdkk=filename_rdkk,
                filename_siverval=filename_siverval,
            )
        else:
            return jsonify({
                'error': f'Tipe arsip tidak valid: "{archive_type}". Gunakan "reconcile" atau "predict".'
            }), 400

        return jsonify({
            'message': 'Data berhasil disimpan ke arsip.',
            'session_id': result['session_id'],
            'total_saved': result['total_saved'],
        }), 200

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


@archive_bp.route('/api/archive/bulk-delete', methods=['DELETE'])
def bulk_delete_archive():
    """
    Endpoint untuk menghapus beberapa arsip sekaligus.

    Body JSON:
    {
        "type": "reconcile" | "predict",
        "session_ids": [1, 2, 3]
    }
    """
    try:
        from config.supabase_client import get_supabase

        data = request.get_json()

        if not data:
            return jsonify({'error': 'Body JSON tidak boleh kosong.'}), 400

        archive_type = data.get('type')
        session_ids = data.get('session_ids')

        if not archive_type:
            return jsonify({'error': 'Field "type" wajib diisi.'}), 400

        if session_ids is None:
            return jsonify({'error': 'Field "session_ids" wajib diisi.'}), 400

        if not isinstance(session_ids, list) or len(session_ids) == 0:
            return jsonify({'error': 'Field "session_ids" harus berupa list yang tidak kosong.'}), 400

        supabase = get_supabase()

        if archive_type == 'reconcile':
            supabase.table('rekonsiliasi_detail') \
                .delete() \
                .in_('session_id', session_ids) \
                .execute()
            result = supabase.table('rekonsiliasi_sessions') \
                .delete() \
                .in_('id', session_ids) \
                .execute()
        elif archive_type == 'predict':
            supabase.table('prediksi_detail') \
                .delete() \
                .in_('session_id', session_ids) \
                .execute()
            result = supabase.table('prediksi_sessions') \
                .delete() \
                .in_('id', session_ids) \
                .execute()
        else:
            return jsonify({
                'error': f'Tipe arsip tidak valid: "{archive_type}". Gunakan "reconcile" atau "predict".'
            }), 400

        deleted_count = len(result.data) if result.data else 0

        return jsonify({
            'message': f'Berhasil menghapus {deleted_count} sesi arsip.',
            'deleted_count': deleted_count,
        }), 200

    except Exception as e:
        return jsonify({'error': f'Gagal menghapus arsip: {str(e)}'}), 500