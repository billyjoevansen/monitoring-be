from flask import Blueprint, jsonify
from config.supabase_client import get_supabase_admin
import json

stats_bp = Blueprint('stats', __name__)


def parse_json(value):
    """Parse JSONB field — bisa berupa dict atau string."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


@stats_bp.route('/api/stats/summary', methods=['GET'])
def stats_summary():
    """Ringkasan statistik global dari seluruh arsip rekonsiliasi dan klasifikasi."""
    try:
        supabase = get_supabase_admin()

        # Ambil semua summary dari reconciliation_archives
        recs = (
            supabase.table('reconciliation_archives')
            .select('summary')
            .execute()
        )

        # Agregasi rekonsiliasi
        total_rec_archives = len(recs.data) if recs.data else 0
        total_petani_rec = 0
        total_lengkap = 0
        total_sebagian = 0
        total_melebihi = 0
        total_belum = 0

        for row in (recs.data or []):
            summary = parse_json(row.get('summary'))
            total_petani_rec += summary.get('total_petani', 0)
            sp = parse_json(summary.get('status_penebusan'))
            total_lengkap += sp.get('tebus_lengkap', 0)
            total_sebagian += sp.get('tebus_sebagian', 0)
            total_melebihi += sp.get('tebus_melebihi', 0)
            total_belum += sp.get('belum_menebus', 0)

        persentase_lengkap = (
            round((total_lengkap / total_petani_rec * 100), 1)
            if total_petani_rec > 0 else 0
        )

        # Ambil semua summary & model_info dari classification_archives
        cls = (
            supabase.table('classification_archives')
            .select('summary,model_info')
            .execute()
        )

        total_cls_archives = len(cls.data) if cls.data else 0
        total_petani_cls = 0
        sum_akurasi = 0
        sum_persentase_normal = 0
        count_model = 0

        for row in (cls.data or []):
            summary = parse_json(row.get('summary'))
            total_petani_cls += summary.get('total_petani', 0)
            sum_persentase_normal += summary.get('persentase_normal', 0)

            model_info = parse_json(row.get('model_info'))
            if model_info and model_info.get('accuracy') is not None:
                sum_akurasi += model_info['accuracy']
                count_model += 1

        rata_akurasi = round((sum_akurasi / count_model * 100), 1) if count_model > 0 else 0
        rata_persentase_normal = (
            round(sum_persentase_normal / total_cls_archives, 1)
            if total_cls_archives > 0 else 0
        )

        return jsonify({
            'reconciliation': {
                'total_archives': total_rec_archives,
                'total_petani': total_petani_rec,
                'total_lengkap': total_lengkap,
                'total_sebagian': total_sebagian,
                'total_melebihi': total_melebihi,
                'total_belum': total_belum,
                'persentase_lengkap': persentase_lengkap,
            },
            'classification': {
                'total_archives': total_cls_archives,
                'total_petani': total_petani_cls,
                'rata_rata_akurasi': rata_akurasi,
                'rata_rata_persentase_normal': rata_persentase_normal,
            },
        }), 200

    except Exception as e:
        return jsonify({'error': f'Gagal mengambil statistik: {str(e)}'}), 500
