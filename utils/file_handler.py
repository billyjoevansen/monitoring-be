import pandas as pd
from werkzeug.datastructures import FileStorage


# =====================================================
# KONFIGURASI NAMA KOLOM
# Mapping nama kolom dari Excel ke nama standar internal
# =====================================================

# Kolom RDKK
RDKK_COLUMNS = {
    'Nama Petani': 'nama_petani',
    'KTP': 'nik',
    'Kode Kios Pengecer': 'kode_kios_rdkk',
    'Nama Kios Pengecer': 'nama_kios_rdkk',
    'Nama Poktan': 'poktan',
    'Gapoktan': 'gapoktan',
    'Nama Penyuluh': 'penyuluh',
    'Alamat': 'alamat',
    'Subsektor': 'subsektor',

    # MT1
    'Komoditas MT1': 'komoditas_mt1',
    'Luas Lahan (Ha) MT1': 'luas_lahan_mt1',
    'Pupuk Urea (Kg) MT1': 'urea_mt1',
    'Pupuk NPK (Kg) MT1': 'npk_mt1',
    'Pupuk NPK Formula (Kg) MT1': 'npk_formula_mt1',
    'Pupuk Organik (Kg) MT1': 'organik_mt1',
    'Pupuk ZA (Kg) MT1': 'za_mt1',

    # MT2
    'Komoditas MT2': 'komoditas_mt2',
    'Luas Lahan (Ha) MT2': 'luas_lahan_mt2',
    'Pupuk Urea (Kg) MT2': 'urea_mt2',
    'Pupuk NPK (Kg) MT2': 'npk_mt2',
    'Pupuk NPK Formula (Kg) MT2': 'npk_formula_mt2',
    'Pupuk Organik (Kg) MT2': 'organik_mt2',
    'Pupuk ZA (Kg) MT2': 'za_mt2',

    # MT3
    'Komoditas MT3': 'komoditas_mt3',
    'Luas Lahan (Ha) MT3': 'luas_lahan_mt3',
    'Pupuk Urea (Kg) MT3': 'urea_mt3',
    'Pupuk NPK (Kg) MT3': 'npk_mt3',
    'Pupuk NPK Formula (Kg) MT3': 'npk_formula_mt3',
    'Pupuk Organik (Kg) MT3': 'organik_mt3',
    'Pupuk ZA (Kg) MT3': 'za_mt3',
}

# Kolom SIVERVAL
SIVERVAL_COLUMNS = {
    'NIK': 'nik',
    'nama petani': 'nama_petani_siverval',
    'kode kios': 'kode_kios_siverval',
    'nama kios': 'nama_kios_siverval',
    'urea': 'urea_tebus',
    'npk': 'npk_tebus',
    'sp36': 'sp36_tebus',
    'za': 'za_tebus',
    'npk formula': 'npk_formula_tebus',
    'organik': 'organik_tebus',
    'organik cair': 'organik_cair_tebus',
    'tgl tebus': 'tgl_tebus',
    'tgl input': 'tgl_input',
    'status petani': 'status_petani',
    'Kabupaten': 'kabupaten',
    'kecamatan': 'kecamatan',
}

def parse_excel(file: FileStorage, header_row: int = 0) -> pd.DataFrame:
    """
    Membaca file Excel/CSV yang diupload dan mengembalikan DataFrame.

    Args:
        file: File yang diupload
        header_row: Baris ke-berapa yang jadi header (0-indexed).
                    Default 0 (baris pertama).
    """
    filename = file.filename.lower()

    if filename.endswith('.csv'):
        df = pd.read_csv(file, header=header_row)
    elif filename.endswith(('.xls', '.xlsx')):
        df = pd.read_excel(file, engine='openpyxl', header=header_row)
    else:
        raise ValueError(f"Format file tidak didukung: {filename}. Gunakan .csv, .xls, atau .xlsx")

    return df

def standardize_rdkk(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standarisasi nama kolom RDKK ke format internal.
    """
    # Rename kolom yang cocok
    rename_map = {}
    for original, standard in RDKK_COLUMNS.items():
        # Case-insensitive matching
        for col in df.columns:
            if col.strip().lower() == original.lower():
                rename_map[col] = standard
                break

    df = df.rename(columns=rename_map)

    # Pastikan kolom NIK berupa string
    if 'nik' in df.columns:
        df['nik'] = df['nik'].astype(str).str.strip()

    return df


def standardize_siverval(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standarisasi nama kolom SIVERVAL ke format internal.
    """
    rename_map = {}
    for original, standard in SIVERVAL_COLUMNS.items():
        for col in df.columns:
            if col.strip().lower() == original.lower():
                rename_map[col] = standard
                break

    df = df.rename(columns=rename_map)

    # Pastikan kolom NIK berupa string
    if 'nik' in df.columns:
        df['nik'] = df['nik'].astype(str).str.strip()

    # Konversi kolom numerik pupuk
    pupuk_cols = [
        'urea_tebus', 'npk_tebus', 'sp36_tebus', 'za_tebus',
        'npk_formula_tebus', 'organik_tebus', 'organik_cair_tebus'
    ]
    for col in pupuk_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    return df