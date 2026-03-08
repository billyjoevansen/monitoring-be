from flask import Blueprint, request, jsonify

users_bp = Blueprint('users', __name__)


@users_bp.route('/api/users/bulk-delete', methods=['DELETE'])
def bulk_delete_users():
    """
    Endpoint untuk menghapus beberapa pengguna sekaligus.

    Body JSON:
    {
        "user_ids": ["uuid1", "uuid2", "uuid3"]
    }
    """
    try:
        from config.supabase_client import get_supabase

        data = request.get_json()

        if not data:
            return jsonify({'error': 'Body JSON tidak boleh kosong.'}), 400

        user_ids = data.get('user_ids')

        if user_ids is None:
            return jsonify({'error': 'Field "user_ids" wajib diisi.'}), 400

        if not isinstance(user_ids, list) or len(user_ids) == 0:
            return jsonify({'error': 'Field "user_ids" harus berupa list yang tidak kosong.'}), 400

        supabase = get_supabase()

        result = supabase.table('users') \
            .delete() \
            .in_('id', user_ids) \
            .execute()

        deleted_count = len(result.data) if result.data else 0

        return jsonify({
            'message': f'Berhasil menghapus {deleted_count} pengguna.',
            'deleted_count': deleted_count,
        }), 200

    except Exception as e:
        return jsonify({'error': f'Gagal menghapus pengguna: {str(e)}'}), 500
