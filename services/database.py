import pandas as pd
from datetime import datetime, timezone
from config.supabase_client import get_supabase


def save_reconciliation(summary: dict, detail: list, filename_rdkk: str, filename_siverval: str) -> dict:
    """
    Menyimpan hasil rekonsiliasi ke Supabase.

    Tabel: rekonsiliasi_sessions (ringkasan per sesi)
    Tabel: rekonsiliasi_detail  (detail per petani)
    """
    supabase = get_supabase()
    now = datetime.now(timezone.utc).isoformat()

    # 1. Simpan sesi rekonsiliasi
    session_data = {
        'created_at': now,
        'filename_rdkk': filename_rdkk,
        'filename_siverval': filename_siverval,
        'total_petani': summary['total_petani'],
        'tebus_lengkap': summary['status_penebusan']['tebus_lengkap'],
        'tebus_sebagian': summary['status_penebusan']['tebus_sebagian'],
        'tebus_melebihi': summary['status_penebusan']['tebus_melebihi'],
        'belum_menebus': summary['status_penebusan']['belum_menebus'],
        'kios_sesuai': summary['kios']['sesuai'],
        'kios_tidak_sesuai': summary['kios']['tidak_sesuai'],
        'total_pupuk_diajukan_kg': summary['total_pupuk_diajukan_kg'],
        'total_pupuk_ditebus_kg': summary['total_pupuk_ditebus_kg'],
    }

    result = supabase.table('rekonsiliasi_sessions').insert(session_data).execute()
    session_id = result.data[0]['id']

    # 2. Simpan detail per petani (batch insert)
    detail_records = []
    for petani in detail:
        record = {
            'session_id': session_id,
            'nama_petani': petani['nama_petani'],
            'nik': petani['nik'],
            'poktan': petani['poktan'],
            'gapoktan': petani['gapoktan'],
            'kios_rdkk': petani['kios_rdkk'],
            'kios_penebusan': petani['kios_penebusan'],
            'kios_sesuai': petani['kios_sesuai'],
            'total_pupuk_diajukan_kg': petani['total_pupuk_diajukan_kg'],
            'total_pupuk_ditebus_kg': petani['total_pupuk_ditebus_kg'],
            'selisih_total_kg': petani['selisih_total_kg'],
            'status_tebus': petani['status_tebus'],
        }
        detail_records.append(record)

    # Batch insert (per 500 baris agar tidak timeout)
    batch_size = 500
    for i in range(0, len(detail_records), batch_size):
        batch = detail_records[i:i + batch_size]
        supabase.table('rekonsiliasi_detail').insert(batch).execute()

    return {'session_id': session_id, 'total_saved': len(detail_records)}


def save_prediction(summary: dict, detail: list, filename_rdkk: str, filename_siverval: str) -> dict:
    """
    Menyimpan hasil prediksi model ke Supabase.

    Tabel: prediksi_sessions (ringkasan per sesi)
    Tabel: prediksi_detail   (detail per petani)
    """
    supabase = get_supabase()
    now = datetime.now(timezone.utc).isoformat()

    # 1. Simpan sesi prediksi
    session_data = {
        'created_at': now,
        'filename_rdkk': filename_rdkk,
        'filename_siverval': filename_siverval,
        'total_petani': summary['total_petani'],
        'total_normal': summary['normal'],
        'total_tidak_normal': summary['tidak_normal'],
        'persentase_normal': summary['persentase_normal'],
        'persentase_tidak_normal': summary['persentase_tidak_normal'],
    }

    result = supabase.table('prediksi_sessions').insert(session_data).execute()
    session_id = result.data[0]['id']

    # 2. Simpan detail per petani
    detail_records = []
    for petani in detail:
        record = {
            'session_id': session_id,
            'nama_petani': petani['nama_petani'],
            'nik': petani['nik'],
            'poktan': petani.get('poktan', ''),
            'status': petani['status'],
            'confidence': petani['confidence'],
            'kios_sesuai': petani['kios_sesuai'],
            'total_pupuk_diajukan': petani.get('total_pupuk_diajukan', 0),
            'total_pupuk_ditebus': petani.get('total_pupuk_ditebus', 0),
            'selisih_total_pupuk': petani.get('selisih_total_pupuk', 0),
        }
        detail_records.append(record)

    batch_size = 500
    for i in range(0, len(detail_records), batch_size):
        batch = detail_records[i:i + batch_size]
        supabase.table('prediksi_detail').insert(batch).execute()

    return {'session_id': session_id, 'total_saved': len(detail_records)}