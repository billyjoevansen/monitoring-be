from flask import Blueprint, request, jsonify

logs_bp = Blueprint('logs', __name__)


@logs_bp.route('/api/logs/bulk-delete', methods=['DELETE'])
def bulk_delete_logs():
    """
    Endpoint untuk menghapus beberapa log aktivitas sekaligus.

    Body JSON:
    {
        "log_ids": ["uuid1", "uuid2", "uuid3"]
    }
    """
    try:
        from config.supabase_client import get_supabase

        data = request.get_json()

        if not data:
            return jsonify({'error': 'Body JSON tidak boleh kosong.'}), 400

        log_ids = data.get('log_ids')

        if log_ids is None:
            return jsonify({'error': 'Field "log_ids" wajib diisi.'}), 400

        if not isinstance(log_ids, list) or len(log_ids) == 0:
            return jsonify({'error': 'Field "log_ids" harus berupa list yang tidak kosong.'}), 400

        supabase = get_supabase()

        result = supabase.table('activity_logs') \
            .delete() \
            .in_('id', log_ids) \
            .execute()

        deleted_count = len(result.data) if result.data else 0

        return jsonify({
            'message': f'Berhasil menghapus {deleted_count} log aktivitas.',
            'deleted_count': deleted_count,
        }), 200

    except Exception as e:
        return jsonify({'error': f'Gagal menghapus log aktivitas: {str(e)}'}), 500


@logs_bp.route('/api/logs/clear-all', methods=['DELETE'])
def clear_all_logs():
    """
    Endpoint untuk menghapus semua log aktivitas.
    """
    try:
        from config.supabase_client import get_supabase

        supabase = get_supabase()

        supabase.table('activity_logs') \
            .delete() \
            .neq('id', None) \
            .execute()

        return jsonify({
            'message': 'Semua log aktivitas berhasil dihapus.',
        }), 200

    except Exception as e:
        return jsonify({'error': f'Gagal menghapus semua log aktivitas: {str(e)}'}), 500
