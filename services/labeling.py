import pandas as pd
import numpy as np


def assign_labels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Memberi label NORMAL (0) atau TIDAK NORMAL (1) berdasarkan aturan:

    TIDAK NORMAL jika SALAH SATU kondisi terpenuhi:
    1. Rasio tebus salah satu pupuk > 1.0 (tebus melebihi pengajuan)
    2. Menebus pupuk tapi tidak punya pengajuan di RDKK
    3. Menebus pupuk di luar RDKK (SP36/Organik Cair)
    4. Status petani non-aktif (sesuai PDF)

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

    alasan_list = [[] for _ in range(len(df))]

    for idx in range(len(df)):
        row = df.iloc[idx]
        reasons = []

        # --- Kondisi 1: Rasio tebus > 1.0 (melebihi kuota) ---
        for col in rasio_cols:
            if col in df.columns and row[col] > 1.0 and row[col] != 999.0:
                pupuk_name = col.replace('rasio_tebus_', '').upper()
                reasons.append(
                    f"Rasio tebus {pupuk_name}: {row[col]:.2f} (melebihi pengajuan)"
                )

        # --- Kondisi 2: Tebus tanpa pengajuan (rasio = 999) ---
        for col in rasio_cols:
            if col in df.columns and row[col] == 999.0:
                pupuk_name = col.replace('rasio_tebus_', '').upper()
                reasons.append(
                    f"Menebus {pupuk_name} tanpa pengajuan di RDKK"
                )

        # --- Kondisi 3: Tebus pupuk di luar RDKK (SP36/Organik Cair) ---
        if 'tebus_diluar_rdkk' in df.columns and row['tebus_diluar_rdkk'] == 1:
            reasons.append("Menebus pupuk di luar RDKK (SP36/Organik Cair)")

        # --- Kondisi 4: Status petani non-aktif (sesuai PDF) ---
        if 'status_petani' in df.columns:
            status = str(row['status_petani']).lower().strip()
            if status in ['non-aktif', 'non aktif', 'inactive', 'tidak aktif']:
                reasons.append(f"Status petani: {row['status_petani']}")

        # --- Kondisi 5: Penebusan kurang dari 85% pengajuan ---
        if 'rasio_total_penebusan' in df.columns:
            rasio_total = row['rasio_total_penebusan']
            if 0 < rasio_total < 0.85:
                reasons.append(
                    f"Penebusan hanya {rasio_total*100:.1f}% dari pengajuan (< 85%)"
                )

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