import io
import logging
import pandas as pd
from flask import Blueprint, request, jsonify
from services.kecamatan_lookup import get_kecamatan_from_rdkk, get_kecamatan_from_siverval

documents_bp = Blueprint('documents', __name__)
logger = logging.getLogger(__name__)


@documents_bp.route('/api/identify-kecamatan', methods=['POST'])
def identify_kecamatan():
    """Identifikasi kecamatan dari file Excel RDKK atau SIVERVAL.

    Form data:
        file: File Excel
        document_type: 'rdkk' | 'siverval'

    Returns:
        {"kecamatan": ["Kecamatan Walantaka", "Kecamatan Taktakan", ...]}
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'File tidak ditemukan.'}), 400

        file = request.files['file']
        document_type = request.form.get('document_type', '')

        if document_type not in ('rdkk', 'siverval'):
            return jsonify({'error': 'document_type harus "rdkk" atau "siverval".'}), 400

        # Baca Excel ke DataFrame
        file_bytes = file.read()
        excel_buffer = io.BytesIO(file_bytes)

        if document_type == 'rdkk':
            # RDKK: header di baris pertama (index 0)
            df = pd.read_excel(excel_buffer, engine='openpyxl')
            df.columns = df.columns.str.strip()
            logger.info(f"RDKK kolom terbaca: {list(df.columns)}")
            data = df.fillna('').to_dict(orient='records')
            kecamatan_list = get_kecamatan_from_rdkk(data)
        else:
            # SIVERVAL: header di baris kedua (index 1), ada baris judul
            df = pd.read_excel(excel_buffer, header=1, engine='openpyxl')
            df.columns = df.columns.str.strip()
            logger.info(f"SIVERVAL kolom terbaca: {list(df.columns)}")
            data = df.fillna('').to_dict(orient='records')
            kecamatan_list = get_kecamatan_from_siverval(data)

        logger.info(f"Kecamatan terdeteksi: {kecamatan_list}")

        return jsonify({'kecamatan': kecamatan_list}), 200

    except Exception as e:
        logger.error(f"Gagal identifikasi kecamatan: {e}")
        return jsonify({'error': f'Gagal membaca file: {str(e)}'}), 500
