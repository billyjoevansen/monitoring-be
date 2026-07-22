import base64
import logging
from datetime import date
from flask import Blueprint, request, jsonify
from services.dummy_generator import generate_dummy_data, _load_kecamatan_desa

dummy_bp = Blueprint('dummy', __name__)
logger = logging.getLogger(__name__)


@dummy_bp.route('/api/dummy/generate', methods=['POST'])
def generate_dummy():
    try:
        body = request.get_json(silent=True) or {}

        n_petani = int(body.get('n_petani', 350))
        n_transaksi = int(body.get('n_transaksi', 260))
        seed = body.get('seed', None)

        pct_normal = float(body.get('pct_normal', 50))
        pct_over = float(body.get('pct_over', 8))
        pct_kurang = float(body.get('pct_kurang', 42))
        kecamatan = body.get('kecamatan', None)

        if n_petani < 1 or n_transaksi < 1:
            return jsonify({'error': 'n_petani dan n_transaksi minimal 1'}), 400

        total_pct = pct_normal + pct_over + pct_kurang
        if abs(total_pct - 100) > 0.01:
            return jsonify({'error': f'Persentase harus berjumlah 100% (saat ini {total_pct}%)'}), 400

        if kecamatan:
            kecamatan_data = _load_kecamatan_desa()
            if kecamatan not in kecamatan_data:
                valid = ', '.join(kecamatan_data.keys())
                return jsonify({'error': f"Kecamatan '{kecamatan}' tidak valid. Pilihan: {valid}"}), 400

        rdkk_buf, siverval_buf, summary = generate_dummy_data(
            n_petani=n_petani,
            n_transaksi=n_transaksi,
            seed=seed,
            pct_normal=pct_normal,
            pct_over=pct_over,
            pct_kurang=pct_kurang,
            kecamatan_filter=kecamatan,
        )

        today = date.today().strftime('%d_%m_%Y')
        kec_slug = kecamatan.replace('Kecamatan ', '').lower() if kecamatan else 'semua_kecamatan'
        rdkk_b64 = base64.b64encode(rdkk_buf.getvalue()).decode('utf-8')
        siverval_b64 = base64.b64encode(siverval_buf.getvalue()).decode('utf-8')

        return jsonify({
            'rdkk': {
                'filename': f'rdkk_{kec_slug}_{today}.xlsx',
                'content': rdkk_b64,
            },
            'siverval': {
                'filename': f'verval_{kec_slug}_{today}.xlsx',
                'content': siverval_b64,
            },
            'summary': summary,
        }), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Generate dummy error: {e}", exc_info=True)
        return jsonify({'error': f'Terjadi kesalahan: {str(e)}'}), 500
