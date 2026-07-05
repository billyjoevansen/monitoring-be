import pandas as pd
import numpy as np


def aggregate_rdkk(df: pd.DataFrame) -> pd.DataFrame:
    """
    Menggabungkan data pupuk dari MT1 + MT2 + MT3 menjadi total per petani.
    Karena SIVERVAL adalah data akumulasi (tidak per MT).
    Kemudian groupby NIK agar satu petani = satu baris.
    """
    df = df.copy()

    # --- Total Pupuk Diajukan (MT1 + MT2 + MT3) ---
    pupuk_types = ['urea', 'npk', 'npk_formula', 'organik', 'za']

    for pupuk in pupuk_types:
        mt_cols = [f'{pupuk}_mt1', f'{pupuk}_mt2', f'{pupuk}_mt3']
        existing_cols = [c for c in mt_cols if c in df.columns]
        if existing_cols:
            df[f'{pupuk}_diajukan'] = df[existing_cols].fillna(0).sum(axis=1)
        else:
            df[f'{pupuk}_diajukan'] = 0

    # --- Total Luas Lahan ---
    luas_cols = ['luas_lahan_mt1', 'luas_lahan_mt2', 'luas_lahan_mt3']
    existing_luas = [c for c in luas_cols if c in df.columns]
    if existing_luas:
        df['total_luas_lahan'] = df[existing_luas].fillna(0).sum(axis=1)
    else:
        df['total_luas_lahan'] = 0

    # --- Jumlah Musim Tanam Aktif ---
    def count_mt(row):
        count = 0
        for mt in ['mt1', 'mt2', 'mt3']:
            luas_col = f'luas_lahan_{mt}'
            if luas_col in row.index and pd.notna(row[luas_col]) and row[luas_col] > 0:
                count += 1
        return count

    df['jumlah_mt_aktif'] = df.apply(count_mt, axis=1)

    # --- Total Pupuk Diajukan (semua jenis) ---
    diajukan_cols = [f'{p}_diajukan' for p in pupuk_types]
    df['total_pupuk_diajukan'] = df[diajukan_cols].sum(axis=1)

    # --- Group by NIK (satu petani = satu baris) ---
    # Kolom numerik di-sum, kolom non-numerik diambil 'first'
    if 'nik' in df.columns:
        numeric_cols = df.select_dtypes(include='number').columns.tolist()
        non_numeric_cols = df.select_dtypes(exclude='number').columns.tolist()
        if 'nik' in non_numeric_cols:
            non_numeric_cols.remove('nik')

        agg_dict = {col: 'sum' for col in numeric_cols}
        agg_dict.update({col: 'first' for col in non_numeric_cols})

        df = df.groupby('nik').agg(agg_dict).reset_index()

    return df


def merge_data(rdkk: pd.DataFrame, siverval: pd.DataFrame) -> pd.DataFrame:
    """
    Menggabungkan (merge) data RDKK dan SIVERVAL berdasarkan NIK.
    Menggunakan LEFT JOIN dari RDKK agar semua petani RDKK tetap ada,
    termasuk yang tidak menebus (akan terisi 0).
    """
    # Aggregate RDKK dulu (total dari semua MT + groupby NIK)
    rdkk_agg = aggregate_rdkk(rdkk)

    # Aggregate SIVERVAL per NIK (jika ada transaksi ganda)
    siverval_agg_cols = {
        'urea_tebus': 'sum',
        'npk_tebus': 'sum',
        'za_tebus': 'sum',
        'npk_formula_tebus': 'sum',
        'organik_tebus': 'sum',
        'sp36_tebus': 'sum',
        'organik_cair_tebus': 'sum',
    }

    # Hanya aggregate kolom yang ada
    existing_agg = {k: v for k, v in siverval_agg_cols.items() if k in siverval.columns}

    # Kolom non-numerik yang ingin dipertahankan
    keep_first = {}
    for col in ['kode_kios_siverval', 'nama_kios_siverval', 'kabupaten', 'kecamatan']:
        if col in siverval.columns:
            keep_first[col] = 'first'

    # Kolom tanggal dan status — ambil max (transaksi terakhir)
    keep_max = {}
    for col in ['tgl_tebus', 'tgl_input']:
        if col in siverval.columns:
            keep_max[col] = 'max'

    # Kolom status — ambil value pertama
    for col in ['status_petani']:
        if col in siverval.columns:
            keep_first[col] = 'first'

    # Kolom no_transaksi — hitung jumlah transaksi
    count_cols = {}
    if 'no_transaksi' in siverval.columns:
        count_cols['no_transaksi'] = 'count'

    siverval_grouped = siverval.groupby('nik').agg({
        **existing_agg,
        **keep_first,
        **keep_max,
        **count_cols,
    }).reset_index()

    # Rename no_transaksi count → frekuensi_transaksi
    if 'no_transaksi' in siverval_grouped.columns:
        siverval_grouped = siverval_grouped.rename(
            columns={'no_transaksi': 'frekuensi_transaksi'}
        )

    # Merge
    merged = rdkk_agg.merge(siverval_grouped, on='nik', how='left')

    # Isi NaN dengan 0 untuk kolom tebus (petani yang tidak menebus)
    # KECUALI kolom tanggal (tgl_tebus, tgl_input) — biarkan NaT
    tebus_cols = [c for c in merged.columns if '_tebus' in c and c not in ('tgl_tebus',)]
    merged[tebus_cols] = merged[tebus_cols].fillna(0)

    # Isi NaN frekuensi_transaksi dengan 0 (petani yang tidak menebus)
    if 'frekuensi_transaksi' in merged.columns:
        merged['frekuensi_transaksi'] = merged['frekuensi_transaksi'].fillna(0).astype(int)

    # Pastikan kolom tanggal tetap bertipe datetime setelah merge
    for col in ['tgl_tebus', 'tgl_input']:
        if col in merged.columns:
            merged[col] = pd.to_datetime(merged[col], errors='coerce')

    return merged


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Feature engineering: menghitung rasio, selisih, dan fitur turunan
    untuk input ke model Random Forest.
    """
    df = df.copy()

    # =====================================================
    # 1. RASIO PENEBUSAN PER JENIS PUPUK (untuk labeling)
    # =====================================================
    pupuk_mapping = {
        'urea': ('urea_tebus', 'urea_diajukan'),
        'npk': ('npk_tebus', 'npk_diajukan'),
        'za': ('za_tebus', 'za_diajukan'),
        'npk_formula': ('npk_formula_tebus', 'npk_formula_diajukan'),
        'organik': ('organik_tebus', 'organik_diajukan'),
    }

    rasio_cols = []
    for pupuk, (tebus_col, ajukan_col) in pupuk_mapping.items():
        rasio_col = f'rasio_tebus_{pupuk}'
        if tebus_col in df.columns and ajukan_col in df.columns:
            df[rasio_col] = np.where(
                df[ajukan_col] > 0,
                df[tebus_col] / df[ajukan_col],
                np.where(df[tebus_col] > 0, 999.0, 0.0)
            )
        else:
            df[rasio_col] = 0.0
        rasio_cols.append(rasio_col)

    # =====================================================
    # 2. SELISIH PUPUK (untuk labeling)
    # =====================================================
    for pupuk, (tebus_col, ajukan_col) in pupuk_mapping.items():
        selisih_col = f'selisih_{pupuk}'
        if tebus_col in df.columns and ajukan_col in df.columns:
            df[selisih_col] = df[ajukan_col] - df[tebus_col]
        else:
            df[selisih_col] = 0.0

    # =====================================================
    # 3. TOTAL RASIO PENEBUSAN
    # =====================================================
    def calc_avg_rasio(row):
        valid_rasios = []
        for col in rasio_cols:
            val = row[col]
            if val != 0.0 and val != 999.0:
                valid_rasios.append(val)
        return np.mean(valid_rasios) if valid_rasios else 0.0

    df['rata_rata_rasio_tebus'] = df.apply(calc_avg_rasio, axis=1)

    # =====================================================
    # 4. TOTAL PUPUK DITEBUS
    # =====================================================
    tebus_pupuk_cols = ['urea_tebus', 'npk_tebus', 'za_tebus',
                        'npk_formula_tebus', 'organik_tebus']
    existing_tebus = [c for c in tebus_pupuk_cols if c in df.columns]
    df['total_pupuk_ditebus'] = df[existing_tebus].sum(axis=1)

    # =====================================================
    # 6. SELISIH TOTAL PUPUK
    # =====================================================
    if 'total_pupuk_diajukan' in df.columns:
        df['selisih_total_pupuk'] = df['total_pupuk_diajukan'] - df['total_pupuk_ditebus']
    else:
        df['selisih_total_pupuk'] = 0

    # =====================================================
    # 6b. RASIO TOTAL PENEBUSAN TERHADAP TOTAL PENGAJUAN
    # =====================================================
    df['rasio_total_penebusan'] = np.where(
        df['total_pupuk_diajukan'] > 0,
        df['total_pupuk_ditebus'] / df['total_pupuk_diajukan'],
        0.0
    )

    # =====================================================
    # 7. TEBUS PUPUK DI LUAR RDKK
    # =====================================================
    tebus_diluar = 0
    if 'sp36_tebus' in df.columns:
        tebus_diluar += (df['sp36_tebus'] > 0).astype(int)
    if 'organik_cair_tebus' in df.columns:
        tebus_diluar += (df['organik_cair_tebus'] > 0).astype(int)
    df['tebus_diluar_rdkk'] = (tebus_diluar > 0).astype(int)

    # =====================================================
    # 8. FITUR TIDAK LANGSUNG (UNTUK MODEL - BUKAN LABELING)
    #    Ini yang akan dipelajari model sebagai "pola"
    # =====================================================

    # --- 8a. Pupuk per Hektar (intensitas penggunaan) ---
    df['urea_per_ha'] = np.where(
        df['total_luas_lahan'] > 0,
        df.get('urea_diajukan', 0) / df['total_luas_lahan'],
        0
    )
    df['npk_per_ha'] = np.where(
        df['total_luas_lahan'] > 0,
        df.get('npk_diajukan', 0) / df['total_luas_lahan'],
        0
    )
    df['total_pupuk_per_ha'] = np.where(
        df['total_luas_lahan'] > 0,
        df['total_pupuk_diajukan'] / df['total_luas_lahan'],
        0
    )

    # --- 8b. Proporsi tiap jenis pupuk terhadap total ---
    for pupuk in ['urea', 'npk', 'za', 'npk_formula', 'organik']:
        col_ajukan = f'{pupuk}_diajukan'
        if col_ajukan in df.columns:
            df[f'proporsi_{pupuk}'] = np.where(
                df['total_pupuk_diajukan'] > 0,
                df[col_ajukan] / df['total_pupuk_diajukan'],
                0
            )

    # --- 8c. Proporsi penebusan terhadap total ditebus ---
    for pupuk in ['urea', 'npk', 'za', 'npk_formula', 'organik']:
        col_tebus = f'{pupuk}_tebus'
        if col_tebus in df.columns:
            df[f'proporsi_tebus_{pupuk}'] = np.where(
                df['total_pupuk_ditebus'] > 0,
                df[col_tebus] / df['total_pupuk_ditebus'],
                0
            )

    # --- 8d. Jumlah jenis pupuk yang diajukan (diversitas) ---
    pupuk_ajukan_cols = ['urea_diajukan', 'npk_diajukan', 'za_diajukan',
                         'npk_formula_diajukan', 'organik_diajukan']
    existing_ajukan = [c for c in pupuk_ajukan_cols if c in df.columns]
    df['jenis_pupuk_diajukan'] = (df[existing_ajukan] > 0).sum(axis=1)

    # --- 8f. Jumlah jenis pupuk yang ditebus ---
    pupuk_tebus_cols = ['urea_tebus', 'npk_tebus', 'za_tebus',
                        'npk_formula_tebus', 'organik_tebus']
    existing_tebus2 = [c for c in pupuk_tebus_cols if c in df.columns]
    df['jenis_pupuk_ditebus'] = (df[existing_tebus2] > 0).sum(axis=1)

    # --- 8g. Selisih jenis pupuk (ajukan vs tebus) ---
    df['selisih_jenis_pupuk'] = df['jenis_pupuk_diajukan'] - df['jenis_pupuk_ditebus']

    # --- 8g2. Jumlah jenis pupuk yang over (tebus > diajukan) ---
    over_flags = []
    for pupuk, (tebus_col, ajukan_col) in pupuk_mapping.items():
        if tebus_col in df.columns and ajukan_col in df.columns:
            over_flags.append(df[tebus_col] > df[ajukan_col])
    if over_flags:
        df['jumlah_jenis_over'] = pd.concat(over_flags, axis=1).sum(axis=1).astype(int)
    else:
        df['jumlah_jenis_over'] = 0

    # --- 8g3. Jumlah jenis pupuk yang ditebus tanpa pengajuan (rasio = 999) ---
    tidak_diajukan_flags = []
    for pupuk, (tebus_col, ajukan_col) in pupuk_mapping.items():
        if tebus_col in df.columns and ajukan_col in df.columns:
            tidak_diajukan_flags.append((df[tebus_col] > 0) & (df[ajukan_col] == 0))
    if tidak_diajukan_flags:
        df['jumlah_jenis_tidak_diajukan'] = pd.concat(tidak_diajukan_flags, axis=1).sum(axis=1).astype(int)
    else:
        df['jumlah_jenis_tidak_diajukan'] = 0

    # --- 8g4. Proporsi jenis over terhadap jenis yang diajukan ---
    df['proporsi_over'] = np.where(
        df['jenis_pupuk_diajukan'] > 0,
        df['jumlah_jenis_over'] / df['jenis_pupuk_diajukan'],
        0.0
    )

    # --- 8h. Apakah petani menebus pupuk sama sekali ---
    df['ada_penebusan'] = (df['total_pupuk_ditebus'] > 0).astype(int)

    # --- 8i. Rata-rata pupuk per MT ---
    df['rata_pupuk_per_mt'] = np.where(
        df['jumlah_mt_aktif'] > 0,
        df['total_pupuk_diajukan'] / df['jumlah_mt_aktif'],
        0
    )

    # =====================================================
    # 9. FITUR BARU (SESUAI PDF - FITUR REKONSILIASI)
    # =====================================================

    # --- 9a. Flag Melebihi Kuota (binary: ada pupuk yang ditebus > alokasi) ---
    melebihi_flags = []
    for pupuk, (tebus_col, ajukan_col) in pupuk_mapping.items():
        if tebus_col in df.columns and ajukan_col in df.columns:
            melebihi_flags.append(df[tebus_col] > df[ajukan_col])
    if melebihi_flags:
        df['flag_melebihi_kuota'] = pd.concat(melebihi_flags, axis=1).any(axis=1).astype(int)
    else:
        df['flag_melebihi_kuota'] = 0

    return df


# =====================================================
# FITUR UNTUK LABELING (rule-based) - dipakai di labeling.py
# =====================================================
LABEL_FEATURES = [
    'rasio_tebus_urea',
    'rasio_tebus_npk',
    'rasio_tebus_za',
    'rasio_tebus_npk_formula',
    'rasio_tebus_organik',
    'selisih_urea',
    'selisih_npk',
    'selisih_za',
    'selisih_npk_formula',
    'selisih_organik',
    'tebus_diluar_rdkk',
    'flag_melebihi_kuota',
    'status_petani',
]


# =====================================================
# FITUR UNTUK MODEL (tidak langsung = model belajar pola)
# =====================================================
FEATURE_COLUMNS = [
    # Fitur dasar
    'total_luas_lahan',
    'jumlah_mt_aktif',
    'total_pupuk_diajukan',
    'total_pupuk_ditebus',

    # Intensitas per hektar
    'urea_per_ha',
    'npk_per_ha',
    'total_pupuk_per_ha',

    # Proporsi pengajuan
    'proporsi_urea',
    'proporsi_npk',

    # Proporsi penebusan
    'proporsi_tebus_urea',
    'proporsi_tebus_npk',

    # Diversitas
    'jenis_pupuk_ditebus',
    'selisih_jenis_pupuk',

    # Anomali komposit (bukan per-jenis → hindari leakage langsung)
    'jumlah_jenis_over',
    'jumlah_jenis_tidak_diajukan',
    'proporsi_over',

    # Pola perilaku
    'ada_penebusan',
    'rata_pupuk_per_mt',
    'frekuensi_transaksi',

    # Flag
    'flag_melebihi_kuota',
]