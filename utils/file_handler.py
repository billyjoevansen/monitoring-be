import os
import pandas as pd
from werkzeug.datastructures import FileStorage

# =====================================================
# KONFIGURASI NAMA KOLOM
# =====================================================

ALLOWED_EXTENSIONS = {'.xlsx', '.xls'}

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
    'NAMA PETANI': 'nama_petani_siverval',
    'KODE KIOS': 'kode_kios_siverval',
    'NAMA KIOS': 'nama_kios_siverval',
    'UREA': 'urea_tebus',
    'NPK': 'npk_tebus',
    'SP36': 'sp36_tebus',
    'ZA': 'za_tebus',
    'NPK FORMULA': 'npk_formula_tebus',
    'ORGANIK': 'organik_tebus',
    'ORGANIK CAIR': 'organik_cair_tebus',
    'TGL TEBUS': 'tgl_tebus',
    'TGL INPUT': 'tgl_input',
    'STATUS': 'status_petani',
    'KABUPATEN': 'kabupaten',
    'KECAMATAN': 'kecamatan',
}

def validate_file_type(file: FileStorage) -> None:
    """Validate that the uploaded file is an Excel file."""
    if not file.filename:
        raise ValueError("Nama file tidak boleh kosong.")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f'Format file tidak didukung: "{ext}". '
            f'Gunakan file Excel (.xlsx atau .xls).'
        )


def parse_excel(file: FileStorage, header_row: int = 0) -> pd.DataFrame:
    validate_file_type(file)

    try:
        df = pd.read_excel(file, engine='openpyxl', header=header_row)
    except Exception as e:
        raise ValueError(
            f'Gagal membaca file Excel "{file.filename}". '
            f'Pastikan file tidak corrupt dan formatnya benar. '
            f'Detail: {e}'
        )

    if df.empty:
        raise ValueError(f'File "{file.filename}" tidak memiliki data.')

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

    # kolom NIK = string
    if 'nik' in df.columns:
        df['nik'] = df['nik'].astype(str).str.strip().str.lstrip("'")

    # Nilai Record 'Gapoktan'
    if 'gapoktan' not in df.columns:
        df['gapoktan'] = ''
    else:
        df['gapoktan'] = df['gapoktan'].fillna('').astype(str).str.strip()

    # NaN pada kolom pupuk dan luas lahan = 0
    numeric_prefixes = ('urea_', 'npk_', 'npk_formula_', 'organik_', 'za_', 'luas_lahan_')
    for col in df.columns:
        if any(col.startswith(p) for p in numeric_prefixes):
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

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

    # kolom NIK = string
    if 'nik' in df.columns:
        df['nik'] = df['nik'].astype(str).str.strip().str.lstrip("'")
        df = df[df['nik'].notna() & (df['nik'] != '') & (df['nik'] != 'nan')]

    # Pencegahan error nan karena ada 
    if 'NO' in df.columns:
        def is_numeric_row(val):
            try:
                float(str(val).strip().lstrip("'"))
                return True
            except (ValueError, TypeError):
                return False
        df = df[df['NO'].apply(is_numeric_row)]

    pupuk_cols = [
        'urea_tebus', 'npk_tebus', 'sp36_tebus', 'za_tebus',
        'npk_formula_tebus', 'organik_tebus', 'organik_cair_tebus'
    ]
    for col in pupuk_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    return df