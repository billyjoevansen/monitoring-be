from flask import Blueprint, request, jsonify

logs_bp = Blueprint('logs', __name__)


@logs_bp.route('/api/logs/bulk-delete', methods=['POST'])
def bulk_delete_logs():
    """
    Endpoint untuk menghapus beberapa log aktivitas sekaligus berdasarkan log_ids.

    Body JSON:
    {
        "log_ids": ["uuid1", "uuid2", "uuid3"]
    }
    """
    try:
        from config.supabase_client import get_supabase

        data = request.get_json(silent=True)

        if not data:
            return jsonify({'error': 'Body JSON tidak boleh kosong.'}), 400

        log_ids = data.get('log_ids')

        if not log_ids or not isinstance(log_ids, list):
            return jsonify({'error': 'Field "log_ids" wajib diisi dan harus berupa list.'}), 400

        supabase = get_supabase()

        result = supabase.table('activity_logs') \
            .delete() \
            .in_('id', log_ids) \
            .execute()

        total_deleted = len(result.data) if result.data else 0

        return jsonify({
            'message': f'Berhasil menghapus {total_deleted} log aktivitas.',
            'total_deleted': total_deleted,
        }), 200

    except Exception as e:
        return jsonify({'error': f'Gagal menghapus log aktivitas: {str(e)}'}), 500
