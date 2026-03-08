from flask import Blueprint, request, jsonify

users_bp = Blueprint('users', __name__)


@users_bp.route('/api/users/bulk-delete', methods=['POST'])
def bulk_delete_users():
    """
    Endpoint untuk menghapus beberapa pengguna sekaligus berdasarkan user_ids.

    Body JSON:
    {
        "user_ids": ["uuid1", "uuid2", "uuid3"]
    }
    """
    try:
        from config.supabase_client import get_supabase

        data = request.get_json(silent=True)

        if not data:
            return jsonify({'error': 'Body JSON tidak boleh kosong.'}), 400

        user_ids = data.get('user_ids')

        if not user_ids or not isinstance(user_ids, list):
            return jsonify({'error': 'Field "user_ids" wajib diisi dan harus berupa list.'}), 400

        supabase = get_supabase()

        result = supabase.table('users') \
            .delete() \
            .in_('id', user_ids) \
            .execute()

        total_deleted = len(result.data) if result.data else 0

        return jsonify({
            'message': f'Berhasil menghapus {total_deleted} pengguna.',
            'total_deleted': total_deleted,
        }), 200

    except Exception as e:
        return jsonify({'error': f'Gagal menghapus pengguna: {str(e)}'}), 500
