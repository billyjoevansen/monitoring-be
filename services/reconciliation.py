import pandas as pd
import numpy as np


def reconcile(df: pd.DataFrame) -> dict:
    """
    Menghasilkan output rekonsiliasi antara data RDKK dan SIVERVAL.

    Output ini MURNI perbandingan data tanpa melibatkan model ML.
    Tujuannya agar pengguna bisa melihat:
    - Berapa pupuk yang diajukan vs ditebus
    - Apakah kios penebusan sesuai
    - Siapa saja yang belum menebus
    """
    df = df.copy()

    # =====================================================
    # 1. STATUS PENEBUSAN PER PETANI
    # =====================================================
    pupuk_types = ['urea', 'npk', 'za', 'npk_formula', 'organik']

    def get_status_tebus(row):
        """Menentukan status penebusan petani."""
        total_diajukan = row.get('total_pupuk_diajukan', 0)
        total_ditebus = row.get('total_pupuk_ditebus', 0)

        if total_diajukan == 0:
            return 'TIDAK ADA PENGAJUAN'
        elif total_ditebus == 0:
            return 'BELUM MENEBUS'
        elif total_ditebus == total_diajukan:
            return 'TEBUS LENGKAP'
        elif total_ditebus < total_diajukan:
            return 'TEBUS SEBAGIAN'
        else:
            return 'TEBUS MELEBIHI'

    df['status_tebus'] = df.apply(get_status_tebus, axis=1)

    # =====================================================
    # 2. DETAIL REKONSILIASI PER PETANI
    # =====================================================
    detail = []
    for _, row in df.iterrows():
        # Detail per jenis pupuk
        pupuk_detail = {}
        catatan = []

        for pupuk in pupuk_types:
            diajukan = float(row.get(f'{pupuk}_diajukan', 0))
            ditebus = float(row.get(f'{pupuk}_tebus', 0))
            selisih = diajukan - ditebus
            rasio = float(row.get(f'rasio_tebus_{pupuk}', 0))

            status_pupuk = 'SESUAI'
            if diajukan == 0 and ditebus == 0:
                status_pupuk = 'TIDAK DIAJUKAN'
            elif diajukan == 0 and ditebus > 0:
                status_pupuk = 'TANPA PENGAJUAN'
                catatan.append(f'{pupuk.upper()}: Menebus {ditebus:.0f} kg tanpa pengajuan')
            elif ditebus == 0:
                status_pupuk = 'BELUM DITEBUS'
                catatan.append(f'{pupuk.upper()}: Belum ditebus ({diajukan:.0f} kg)')
            elif selisih > 0:
                status_pupuk = 'KURANG'
                catatan.append(f'{pupuk.upper()}: Kurang {selisih:.0f} kg')
            elif selisih < 0:
                status_pupuk = 'LEBIH'
                catatan.append(f'{pupuk.upper()}: Lebih {abs(selisih):.0f} kg')

            pupuk_detail[pupuk] = {
                'diajukan_kg': diajukan,
                'ditebus_kg': ditebus,
                'selisih_kg': round(selisih, 2),
                'rasio': round(rasio, 2),
                'status': status_pupuk,
            }

        # Pupuk di luar RDKK (SP36, Organik Cair)
        sp36 = float(row.get('sp36_tebus', 0))
        organik_cair = float(row.get('organik_cair_tebus', 0))
        if sp36 > 0:
            catatan.append(f'SP36: Menebus {sp36:.0f} kg (tidak ada di RDKK)')
        if organik_cair > 0:
            catatan.append(f'Organik Cair: Menebus {organik_cair:.0f} kg (tidak ada di RDKK)')

        # Kios
        kios_sesuai = bool(row.get('kios_sesuai', True))
        if not kios_sesuai:
            kios_rdkk = str(row.get('nama_kios_rdkk', '-'))
            kios_siverval = str(row.get('nama_kios_siverval', '-'))
            catatan.append(f'Kios tidak sesuai: RDKK={kios_rdkk}, Tebus={kios_siverval}')

        petani = {
            'nama_petani': str(row.get('nama_petani', '')),
            'nik': str(row.get('nik', '')),
            'poktan': str(row.get('poktan', '')),
            'gapoktan': str(row.get('gapoktan', '')) if pd.notna(row.get('gapoktan')) else '',
            'alamat': str(row.get('alamat', '')),
            'penyuluh': str(row.get('penyuluh', '')),
            'kios_rdkk': str(row.get('nama_kios_rdkk', '')),
            'kios_penebusan': str(row.get('nama_kios_siverval', '')),
            'kios_sesuai': kios_sesuai,
            'total_luas_lahan_ha': float(row.get('total_luas_lahan', 0)),
            'jumlah_mt_aktif': int(row.get('jumlah_mt_aktif', 0)),
            'pupuk': pupuk_detail,
            'sp36_tebus_kg': sp36,
            'organik_cair_tebus_kg': organik_cair,
            'total_pupuk_diajukan_kg': float(row.get('total_pupuk_diajukan', 0)),
            'total_pupuk_ditebus_kg': float(row.get('total_pupuk_ditebus', 0)),
            'selisih_total_kg': float(row.get('selisih_total_pupuk', 0)),
            'status_tebus': row.get('status_tebus', ''),
            'catatan': catatan,
        }
        detail.append(petani)

    # =====================================================
    # 3. RINGKASAN REKONSILIASI
    # =====================================================
    total = len(df)
    status_counts = df['status_tebus'].value_counts().to_dict()

    # Ringkasan per jenis pupuk
    pupuk_summary = {}
    for pupuk in pupuk_types:
        diajukan_col = f'{pupuk}_diajukan'
        tebus_col = f'{pupuk}_tebus'
        if diajukan_col in df.columns and tebus_col in df.columns:
            total_diajukan = float(df[diajukan_col].sum())
            total_ditebus = float(df[tebus_col].sum())
            pupuk_summary[pupuk] = {
                'total_diajukan_kg': total_diajukan,
                'total_ditebus_kg': total_ditebus,
                'selisih_kg': round(total_diajukan - total_ditebus, 2),
                'persentase_tebus': round(
                    (total_ditebus / total_diajukan * 100) if total_diajukan > 0 else 0, 2
                ),
            }

    # Kios
    kios_sesuai_count = int(df['kios_sesuai'].sum()) if 'kios_sesuai' in df.columns else total
    kios_tidak_sesuai_count = total - kios_sesuai_count

    summary = {
        'total_petani': total,
        'status_penebusan': {
            'tebus_lengkap': int(status_counts.get('TEBUS LENGKAP', 0)),
            'tebus_sebagian': int(status_counts.get('TEBUS SEBAGIAN', 0)),
            'tebus_melebihi': int(status_counts.get('TEBUS MELEBIHI', 0)),
            'belum_menebus': int(status_counts.get('BELUM MENEBUS', 0)),
            'tidak_ada_pengajuan': int(status_counts.get('TIDAK ADA PENGAJUAN', 0)),
        },
        'kios': {
            'sesuai': kios_sesuai_count,
            'tidak_sesuai': kios_tidak_sesuai_count,
            'persentase_sesuai': round(kios_sesuai_count / total * 100, 2) if total > 0 else 0,
        },
        'pupuk': pupuk_summary,
        'total_pupuk_diajukan_kg': float(df['total_pupuk_diajukan'].sum()) if 'total_pupuk_diajukan' in df.columns else 0,
        'total_pupuk_ditebus_kg': float(df['total_pupuk_ditebus'].sum()) if 'total_pupuk_ditebus' in df.columns else 0,
    }

    return {
        'summary': summary,
        'detail': detail,
    }