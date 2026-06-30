from flask import Blueprint, jsonify
from config.supabase_client import get_supabase_admin
import json
import logging

logger = logging.getLogger(__name__)

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

        # Hitung jumlah dokumen RDKK dan SIVerval + total petani dari supporting_documents
        rdkk_docs = (
            supabase.table('supporting_documents')
            .select('*')
            .eq('document_type', 'rdkk')
            .execute()
        )
        total_rdkk_docs = len(rdkk_docs.data) if rdkk_docs.data else 0
        total_petani_rec = sum(d.get('total_petani', 0) for d in (rdkk_docs.data or []))
        logger.info(f"RDKK docs: {total_rdkk_docs}, total_petani: {total_petani_rec}, data: {rdkk_docs.data}")

        siverval_docs = (
            supabase.table('supporting_documents')
            .select('*')
            .eq('document_type', 'siverval')
            .execute()
        )
        total_siverval_docs = len(siverval_docs.data) if siverval_docs.data else 0
        total_petani_cls = sum(d.get('total_petani', 0) for d in (siverval_docs.data or []))
        logger.info(f"SIVerval docs: {total_siverval_docs}, total_petani: {total_petani_cls}, data: {siverval_docs.data}")

        # Ambil semua summary dari reconciliation_archives (untuk status penebusan)
        recs = (
            supabase.table('reconciliation_archives')
            .select('*')
            .execute()
        )

        # Agregasi status penebusan dari arsip
        total_rec_archives = len(recs.data) if recs.data else 0
        total_lengkap = 0
        total_sebagian = 0
        total_melebihi = 0
        total_belum = 0

        for row in (recs.data or []):
            summary = parse_json(row.get('summary'))
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
            .select('*')
            .execute()
        )

        total_cls_archives = len(cls.data) if cls.data else 0
        sum_akurasi = 0
        sum_persentase_normal = 0
        count_model = 0

        for row in (cls.data or []):
            summary = parse_json(row.get('summary'))
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
                'total_rdkk_docs': total_rdkk_docs,
                'total_petani': total_petani_rec,
                'total_lengkap': total_lengkap,
                'total_sebagian': total_sebagian,
                'total_melebihi': total_melebihi,
                'total_belum': total_belum,
                'persentase_lengkap': persentase_lengkap,
            },
            'classification': {
                'total_siverval_docs': total_siverval_docs,
                'total_petani': total_petani_cls,
                'rata_rata_akurasi': rata_akurasi,
                'rata_rata_persentase_normal': rata_persentase_normal,
            },
        }), 200

    except Exception as e:
        return jsonify({'error': f'Gagal mengambil statistik: {str(e)}'}), 500
