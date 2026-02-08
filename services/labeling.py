import pandas as pd
import numpy as np


def assign_labels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Memberi label NORMAL (0) atau TIDAK NORMAL (1) berdasarkan aturan:

    TIDAK NORMAL jika SALAH SATU kondisi terpenuhi:
    1. Rasio tebus salah satu pupuk > 1.0 (tebus melebihi pengajuan)
    2. Kios penebusan TIDAK sesuai dengan kios RDKK
    3. Selisih (diajukan - ditebus) > 0 (jatah tidak ditebus semua)
    4. Menebus pupuk tapi tidak punya pengajuan di RDKK

    Selain itu → NORMAL
    """
    df = df.copy()

    # Inisialisasi: semua NORMAL (0)
    df['label'] = 0
    df['alasan'] = ''

    rasio_cols = [
        'rasio_tebus_urea', 'rasio_tebus_npk', 'rasio_tebus_za',
        'rasio_tebus_npk_formula', 'rasio_tebus_organik'
    ]

    selisih_cols = [
        'selisih_urea', 'selisih_npk', 'selisih_za',
        'selisih_npk_formula', 'selisih_organik'
    ]

    alasan_list = [[] for _ in range(len(df))]

    for idx in range(len(df)):
        row = df.iloc[idx]
        reasons = []

        # --- Kondisi 1: Rasio tebus > 1.0 ---
        for col in rasio_cols:
            if col in df.columns and row[col] > 1.0 and row[col] != 999.0:
                pupuk_name = col.replace('rasio_tebus_', '').upper()
                reasons.append(
                    f"Rasio tebus {pupuk_name}: {row[col]:.2f} (melebihi pengajuan)"
                )

        # --- Kondisi 2: Kios tidak sesuai ---
        if 'kios_sesuai' in df.columns and row['kios_sesuai'] == 0:
            reasons.append("Kios penebusan tidak sesuai dengan RDKK")

        # --- Kondisi 3: Selisih > 0 (jatah tidak ditebus semua) ---
        for col in selisih_cols:
            if col in df.columns and row[col] > 0:
                pupuk_name = col.replace('selisih_', '').upper()
                reasons.append(
                    f"Selisih {pupuk_name}: {row[col]:.0f} kg (tidak ditebus semua)"
                )

        # --- Kondisi 4: Tebus tanpa pengajuan (rasio = 999) ---
        for col in rasio_cols:
            if col in df.columns and row[col] == 999.0:
                pupuk_name = col.replace('rasio_tebus_', '').upper()
                reasons.append(
                    f"Menebus {pupuk_name} tanpa pengajuan di RDKK"
                )

        # Juga cek SP36 dan Organik Cair (tidak ada di RDKK)
        if 'tebus_diluar_rdkk' in df.columns and row['tebus_diluar_rdkk'] == 1:
            reasons.append("Menebus pupuk di luar RDKK (SP36/Organik Cair)")

        # Set label
        if reasons:
            df.iloc[idx, df.columns.get_loc('label')] = 1  # TIDAK NORMAL
            alasan_list[idx] = reasons

    df['alasan'] = alasan_list

    return df


def get_label_summary(df: pd.DataFrame) -> dict:
    """
    Mengembalikan ringkasan distribusi label.
    """
    total = len(df)
    normal = (df['label'] == 0).sum()
    tidak_normal = (df['label'] == 1).sum()

    return {
        'total_petani': int(total),
        'normal': int(normal),
        'tidak_normal': int(tidak_normal),
        'persentase_normal': round(normal / total * 100, 2) if total > 0 else 0,
        'persentase_tidak_normal': round(tidak_normal / total * 100, 2) if total > 0 else 0,
    }