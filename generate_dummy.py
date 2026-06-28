"""
Script untuk generate data dummy RDKK dan SIVERVAL.
Bisa dijalankan berulang: python generate_dummy.py
File akan otomatis bernama: data_rdkk.xlsx, data_rdkk_1.xlsx, data_rdkk_2.xlsx, dst.
"""
import pandas as pd
import numpy as np
import os
import glob
import sys

# Tambah path backend agar bisa import modul
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

# Jumlah petani dummy
N_PETANI = 500


def fetch_kecamatan_desa():
    """Ambil data kecamatan & desa dari Supabase.
    Return: dict {kecamatan_upper: [(kode_desa, nama_desa), ...]}
    """
    try:
        from config.supabase_client import get_supabase
        supabase = get_supabase()
        result = supabase.table('kecamatan_desa').select('kode_desa, nama_desa, kecamatan').execute()
        rows = result.data or []
        if not rows:
            raise ValueError("Tabel kecamatan_desa kosong")

        mapping = {}
        for row in rows:
            kec = str(row['kecamatan']).strip().title()
            mapping.setdefault(kec, []).append((str(row['kode_desa']).strip(), str(row['nama_desa']).strip()))
        print(f"  [OK] Ambil {len(rows)} desa dari Supabase ({len(mapping)} kecamatan)")
        return mapping
    except Exception as e:
        print(f"  [WARN] Gagal ambil dari Supabase: {e}")
        print("  -> Pakai data hardcoded fallback")
        return {
            'WALANTAKA': [('3673011001', 'WALANTAKA'), ('3673011002', 'CIGOONG'), ('3673011003', 'KALODRAN')],
            'CURUG': [('3673011004', 'CURUG'), ('3673011005', 'CIPETE'), ('3673011006', 'CURUG MANIS')],
            'CIPOCOK JAYA': [('3673011007', 'BANJARSARI'), ('3673011008', 'DALUNG'), ('3673011009', 'GELAM')],
            'KASEMEN': [('3673011010', 'KASEMEN'), ('3673011011', 'BANTEN'), ('3673011012', 'BENDUNG')],
            'TAKTAKAN': [('3673011013', 'TAKTAKAN'), ('3673011014', 'CILOWONG'), ('3673011015', 'DRANGONG')],
            'SERANG': [('3673011016', 'SERANG'), ('3673011017', 'CIPARE'), ('3673011018', 'KOTA BARU')],
        }


def get_next_file_number(folder: str) -> str:
    """
    Menentukan suffix angka berikutnya berdasarkan file yang sudah ada.
    - Pertama kali: data_rdkk.xlsx (tanpa angka)
    - Kedua kali:   data_rdkk_1.xlsx
    - Ketiga kali:  data_rdkk_2.xlsx
    - dst...
    """
    existing = glob.glob(os.path.join(folder, 'data_rdkk*.xlsx'))

    if not existing:
        return ''  # file pertama tanpa suffix

    # Cari angka tertinggi
    max_num = -1
    for filepath in existing:
        filename = os.path.basename(filepath)
        if filename == 'data_rdkk.xlsx':
            max_num = max(max_num, 0)
        elif filename.startswith('data_rdkk_'):
            try:
                num = int(filename.replace('data_rdkk_', '').replace('.xlsx', ''))
                max_num = max(max_num, num)
            except ValueError:
                continue

    next_num = max_num + 1
    if next_num == 0:
        return ''
    return f'_{next_num}'


def generate_dummy():
    # Random seed berbeda setiap kali (berdasarkan file yang sudah ada)
    os.makedirs('dummy_data', exist_ok=True)
    suffix = get_next_file_number('dummy_data')
    seed = abs(hash(suffix)) % (2**31)
    np.random.seed(seed)

    print("[*] Mengambil data kecamatan/desa dari Supabase...")
    kecamatan_desa_map = fetch_kecamatan_desa()
    kecamatan_list = sorted(kecamatan_desa_map.keys())
    # Flat list semua (kode_desa, nama_desa) untuk dipilih random
    all_desa = [(kd, nd, kec) for kec, items in kecamatan_desa_map.items() for kd, nd in items]

    # =====================================================
    # 1. GENERATE DATA RDKK
    # =====================================================

    # Generate NIK 16 digit
    niks = [f'35{"".join([str(np.random.randint(0, 10)) for _ in range(14)])}' for _ in range(N_PETANI)]

    # Nama-nama dummy
    nama_depan = [
        'Budi', 'Siti', 'Ahmad', 'Dewi', 'Agus', 'Sri', 'Hadi', 'Rina', 'Joko', 'Ani', 'Wahyu', 'Lestari', 'Bambang', 'Nurma', 'Eko','Yanti', 'Dani', 'Wati', 'Rudi', 'Mega','Andi', 'Asep', 'Cecep', 'Dedi', 'Eneng', 'Fajar', 'Gita', 'Hendra','Indra', 'Iwan', 'Kartika', 'Mulyadi', 'Nana', 'Oki', 'Putri','Rahmat', 'Soleh', 'Taufik', 'Ujang', 'Yanto', 'Zaki', 'Fitria', 'Rizky', 'Dewantara', 'Sari', 'Wibowo', 'Yusuf', 'Zainal', 'Fadli', 'Guntur', 'Halim', 'Irfan', 'Jumadi', 'Kusnadi', 'Lukman', 'Mardiana',
        'Slamet', 'Yuli', 'Edi', 'Nina', 'Reno', 'Sari', 'Dewi', 'Hendra', 'Lina',
    ]
    nama_belakang = [
        'Santoso', 'Wijaya', 'Hartono', 'Susanto', 'Rahayu', 'Pratama',
        'Saputra', 'Handayani', 'Kusuma', 'Hidayat', 'Lestari', 'Cahyono',
        'Setiawan', 'Purnama', 'Nugroho', 'Wulandari', 'Suryadi', 'Utami',
        'Mulyana', 'Sudarsono', 'Gunawan', 'Suhendar', 'Heryanto', 'Fauzi',
        'Ardiansyah', 'Siregar', 'Laksana', 'Kurniawan', 'Basri', 'Mahendra',
        'Hafiz', 'Budiman', 'Subagyo', 'Pangestu', 'Sanjaya', 'Permana',
        'Yuliana', 'Zulkarnaen', 'Fitria', 'Rizky', 'Dewantara', 'Sari', 'Wibowo', 'Yusuf', 'Zainal', 'Fadli', 'Guntur', 'Halim', 'Irfan', 'Jumadi', 'Kusnadi', 'Lukman', 'Mardiana',
    ]
    nama_petani = [
        f'{np.random.choice(nama_depan)} {np.random.choice(nama_belakang)}'
        for _ in range(N_PETANI)
    ]

    # Kode dan Nama Kios
    kios_data = {
        'K001': 'Toko Tani Makmur',
        'K002': 'Kios Subur Jaya',
        'K003': 'Tani Sejahtera',
        'K004': 'Pupuk Berkah',
        'K005': 'Sarana Tani Mandiri',
    }
    kode_kios_list = list(kios_data.keys())

    # Poktan dan Gapoktan (daerah Serang/Banten)
    poktan_list = [
    'Sri Rejeki', 'Tani Mulyo', 'Karya Tani', 'Maju Jaya', 'Sawit Berkah',
    'Harapan Baru', 'Mekar Sari', 'Subur Makmur', 'Berkah Tani',
    'Sinar Jaya', 'Menteng Jaya', 'Sinar Melati', 'Mina Mukti', 'Sumber Jaya',
    'Pandan Wangi', 'Setia Kawan', 'Taruna Mekar', 'Bina Tani', 'Tani Rahayu',
    'Sida Mukti', 'Maju Bersama', 'Tani Mandiri', 'Hurip', 'Mutiara Tani',
    'Cipta Karya', 'Tunas Harapan', 'Sari Bumi', 'Agro Lestari', 'Tani Sejahtera'
    ]

    # Daerah (Serang & Banten)
    tempat_lahir_list = [
    'Rangkas Bitung', 'Merak', 'Serang', 'Pandeglang',
    'Puloampel', 'Bekasi', 'Tangerang', 'Lampung',
    'Jakarta', 'Bandung', 'Bogor', 'Cilegon', 'Sukabumi', 
    'Semarang', 'Yogyakarta', 'Surakarta', 'Surabaya', 'Malang',
    'Medan', 'Palembang', 'Padang', 'Pekanbaru', 'Banjarmasin', 
    'Pontianak', 'Balikpapan', 'Makassar', 'Manado', 'Denpasar', 
    'Mataram', 'Kupang', 'Ambon', 'Jayapura'
    ]
    kabupaten_list = [
        'Kota Serang', 'Kab. Serang', 'Kab. Pandeglang',
        'Kab. Lebak', 'Kota Cilegon',
    ]

    # Pilih kecamatan & desa untuk setiap petani dari data Supabase
    petani_kecamatan = []  # simpan kecamatan tiap petani untuk sinkronisasi SIVERVAL
    petani_kode_desa = []
    petani_nama_desa = []
    for _ in range(N_PETANI):
        kd, nd, kec = all_desa[np.random.randint(0, len(all_desa))]
        petani_kecamatan.append(kec)
        petani_kode_desa.append(kd)
        petani_nama_desa.append(nd)

    # Komoditas
    komoditas_list = ['Padi', 'Jagung', 'Kedelai', 'Cabai', 'Bawang Merah']

    rdkk_data = {
        'Nama Penyuluh': [f'Penyuluh {chr(65 + i % 10)}' for i in range(N_PETANI)],
        'Kode Desa': petani_kode_desa,
        'Kode Kios Pengecer': [np.random.choice(kode_kios_list) for _ in range(N_PETANI)],
        'Nama Kios Pengecer': [],
        'Gapoktan': [None] * N_PETANI,
        'Nama Poktan': [np.random.choice(poktan_list) for _ in range(N_PETANI)],
        'Nama Petani': nama_petani,
        'KTP': niks,
        'Tempat Lahir': [np.random.choice(tempat_lahir_list) for _ in range(N_PETANI)],
        'Tanggal Lahir': [
            f'{np.random.randint(1960, 1995)}-{np.random.randint(1, 13):02d}-{np.random.randint(1, 29):02d}'
            for _ in range(N_PETANI)
        ],
        'Nama Ibu Kandung': [
            f'{np.random.choice(nama_depan)} {np.random.choice(nama_belakang)}'
            for _ in range(N_PETANI)
        ],
        'Alamat': [
            f'Desa {petani_nama_desa[i]} RT {np.random.randint(1, 10):02d}/{np.random.randint(1, 10):02d}'
            for i in range(N_PETANI)
        ],
        'Subsektor': ['Tanaman Pangan'] * N_PETANI,

        # MT1
        'Komoditas MT1': [np.random.choice(komoditas_list) for _ in range(N_PETANI)],
        'Luas Lahan (Ha) MT1': np.round(np.random.uniform(0.25, 3.0, N_PETANI), 2),
        'Pupuk Urea (Kg) MT1': np.random.choice([50, 100, 150, 200, 250, 300], N_PETANI),
        'Pupuk NPK (Kg) MT1': np.random.choice([50, 100, 150, 200, 250], N_PETANI),
        'Pupuk NPK Formula (Kg) MT1': np.random.choice([0, 50, 100, 150], N_PETANI),
        'Pupuk Organik (Kg) MT1': np.random.choice([0, 100, 200, 500], N_PETANI),
        'Pupuk ZA (Kg) MT1': np.random.choice([0, 50, 100, 150], N_PETANI),

        # MT2
        'Komoditas MT2': [np.random.choice(komoditas_list) if np.random.random() > 0.3 else '' for _ in range(N_PETANI)],
        'Luas Lahan (Ha) MT2': [round(np.random.uniform(0.25, 2.0), 2) if np.random.random() > 0.3 else 0 for _ in range(N_PETANI)],
        'Pupuk Urea (Kg) MT2': [np.random.choice([50, 100, 150, 200]) if np.random.random() > 0.3 else 0 for _ in range(N_PETANI)],
        'Pupuk NPK (Kg) MT2': [np.random.choice([50, 100, 150]) if np.random.random() > 0.3 else 0 for _ in range(N_PETANI)],
        'Pupuk NPK Formula (Kg) MT2': [np.random.choice([0, 50, 100]) if np.random.random() > 0.3 else 0 for _ in range(N_PETANI)],
        'Pupuk Organik (Kg) MT2': [np.random.choice([0, 100, 200]) if np.random.random() > 0.3 else 0 for _ in range(N_PETANI)],
        'Pupuk ZA (Kg) MT2': [np.random.choice([0, 50, 100]) if np.random.random() > 0.3 else 0 for _ in range(N_PETANI)],

        # MT3
        'Komoditas MT3': [np.random.choice(komoditas_list) if np.random.random() > 0.7 else '' for _ in range(N_PETANI)],
        'Luas Lahan (Ha) MT3': [round(np.random.uniform(0.25, 1.5), 2) if np.random.random() > 0.7 else 0 for _ in range(N_PETANI)],
        'Pupuk Urea (Kg) MT3': [np.random.choice([50, 100, 150]) if np.random.random() > 0.7 else 0 for _ in range(N_PETANI)],
        'Pupuk NPK (Kg) MT3': [np.random.choice([50, 100]) if np.random.random() > 0.7 else 0 for _ in range(N_PETANI)],
        'Pupuk NPK Formula (Kg) MT3': [np.random.choice([0, 50]) if np.random.random() > 0.7 else 0 for _ in range(N_PETANI)],
        'Pupuk Organik (Kg) MT3': [np.random.choice([0, 100]) if np.random.random() > 0.7 else 0 for _ in range(N_PETANI)],
        'Pupuk ZA (Kg) MT3': [np.random.choice([0, 50]) if np.random.random() > 0.7 else 0 for _ in range(N_PETANI)],
    }

    rdkk_data['Nama Kios Pengecer'] = [kios_data[k] for k in rdkk_data['Kode Kios Pengecer']]
    rdkk_df = pd.DataFrame(rdkk_data)

    # =====================================================
    # 2. GENERATE DATA SIVERVAL
    # =====================================================

    siverval_records = []
    no = 1

    for i in range(N_PETANI):
        nik = niks[i]
        nama = nama_petani[i]
        kode_kios_rdkk = rdkk_data['Kode Kios Pengecer'][i]

        # Hitung total pupuk diajukan
        urea_rdkk = rdkk_data['Pupuk Urea (Kg) MT1'][i] + rdkk_data['Pupuk Urea (Kg) MT2'][i] + rdkk_data['Pupuk Urea (Kg) MT3'][i]
        npk_rdkk = rdkk_data['Pupuk NPK (Kg) MT1'][i] + rdkk_data['Pupuk NPK (Kg) MT2'][i] + rdkk_data['Pupuk NPK (Kg) MT3'][i]
        za_rdkk = rdkk_data['Pupuk ZA (Kg) MT1'][i] + rdkk_data['Pupuk ZA (Kg) MT2'][i] + rdkk_data['Pupuk ZA (Kg) MT3'][i]
        npk_formula_rdkk = rdkk_data['Pupuk NPK Formula (Kg) MT1'][i] + rdkk_data['Pupuk NPK Formula (Kg) MT2'][i] + rdkk_data['Pupuk NPK Formula (Kg) MT3'][i]
        organik_rdkk = rdkk_data['Pupuk Organik (Kg) MT1'][i] + rdkk_data['Pupuk Organik (Kg) MT2'][i] + rdkk_data['Pupuk Organik (Kg) MT3'][i]

        # Skenario penebusan
        scenario = np.random.random()

        if scenario < 0.35:
            # NORMAL: tebus semua, kios sesuai
            urea_tebus = urea_rdkk
            npk_tebus = npk_rdkk
            za_tebus = za_rdkk
            npk_formula_tebus = npk_formula_rdkk
            organik_tebus = organik_rdkk
            sp36_tebus = 0
            organik_cair_tebus = 0
            kode_kios_tebus = kode_kios_rdkk

        elif scenario < 0.65:
            # Tidak tebus semua (selisih > 0)
            urea_tebus = int(urea_rdkk * np.random.uniform(0.3, 0.9))
            npk_tebus = int(npk_rdkk * np.random.uniform(0.4, 0.95))
            za_tebus = int(za_rdkk * np.random.uniform(0.0, 0.8))
            npk_formula_tebus = int(npk_formula_rdkk * np.random.uniform(0.0, 0.9))
            organik_tebus = int(organik_rdkk * np.random.uniform(0.0, 0.7))
            sp36_tebus = 0
            organik_cair_tebus = 0
            kode_kios_tebus = kode_kios_rdkk

        elif scenario < 0.85:
            # Tebus melebihi pengajuan (rasio > 1)
            urea_tebus = int(urea_rdkk * np.random.uniform(1.1, 2.0))
            npk_tebus = int(npk_rdkk * np.random.uniform(1.0, 1.5))
            za_tebus = int(za_rdkk * np.random.uniform(0.8, 1.3))
            npk_formula_tebus = int(npk_formula_rdkk * np.random.uniform(0.9, 1.2))
            organik_tebus = int(organik_rdkk * np.random.uniform(0.8, 1.1))
            sp36_tebus = 0
            organik_cair_tebus = 0
            kode_kios_tebus = kode_kios_rdkk

        else:
            # Tebus pupuk di luar RDKK (SP36/Organik Cair)
            urea_tebus = int(urea_rdkk * np.random.uniform(0.8, 1.0))
            npk_tebus = int(npk_rdkk * np.random.uniform(0.8, 1.0))
            za_tebus = int(za_rdkk * np.random.uniform(0.5, 1.0))
            npk_formula_tebus = int(npk_formula_rdkk * np.random.uniform(0.5, 1.0))
            organik_tebus = int(organik_rdkk * np.random.uniform(0.5, 1.0))
            sp36_tebus = np.random.choice([50, 100, 150])
            organik_cair_tebus = np.random.choice([0, 20, 50])
            kode_kios_tebus = kode_kios_rdkk

        nama_kios_tebus = kios_data[kode_kios_tebus]

        siverval_records.append({
            'NO': no,
            'KABUPATEN': np.random.choice(kabupaten_list),
            'KECAMATAN': petani_kecamatan[i],
            'NO TRANSAKSI': f'TRX-{2025}-{no:05d}',
            'KODE KIOS': kode_kios_tebus,
            'NAMA KIOS': nama_kios_tebus,
            'NIK': nik,
            'NAMA PETANI': nama,
            'UREA': urea_tebus,
            'NPK': npk_tebus,
            'SP36': sp36_tebus,
            'ZA': za_tebus,
            'NPK FORMULA': npk_formula_tebus,
            'ORGANIK': organik_tebus,
            'ORGANIK CAIR': organik_cair_tebus,
            'TGL TEBUS': f'2025-{np.random.randint(1, 7):02d}-{np.random.randint(1, 29):02d}',
            'TGL INPUT': f'2025-{np.random.randint(1, 7):02d}-{np.random.randint(1, 29):02d}',
            'STATUS PETANI': 'Aktif',
        })
        no += 1

    # Petani tanpa RDKK
    for i in range(10):
        nik_baru = f'35{"".join([str(np.random.randint(0, 10)) for _ in range(14)])}'
        kios_random = np.random.choice(kode_kios_list)
        siverval_records.append({
            'NO': no,
            'KABUPATEN': np.random.choice(kabupaten_list),
            'KECAMATAN': np.random.choice(kecamatan_list),
            'NO TRANSAKSI': f'TRX-{2025}-{no:05d}',
            'KODE KIOS': kios_random,
            'NAMA KIOS': kios_data[kios_random],
            'NIK': nik_baru,
            'NAMA PETANI': f'Petani Tanpa RDKK {i + 1}',
            'UREA': np.random.choice([100, 200]),
            'NPK': np.random.choice([50, 100]),
            'SP36': 0,
            'ZA': np.random.choice([0, 50]),
            'NPK FORMULA': 0,
            'ORGANIK': 0,
            'ORGANIK CAIR': 0,
            'TGL TEBUS': '2025-03-15',
            'TGL INPUT': '2025-03-16',
            'STATUS PETANI': 'Aktif',
        })
        no += 1

    siverval_df = pd.DataFrame(siverval_records)

    # =====================================================
    # 3. TAMBAH NOISE & AMBIGUITAS
    # =====================================================
    for i in range(0, N_PETANI, 5):
        rdkk_df.loc[i, 'Luas Lahan (Ha) MT1'] = round(np.random.uniform(0.1, 0.3), 2)

    for i in range(0, len(siverval_df) - 10, 7):
        faktor_noise = np.random.uniform(0.85, 1.15)
        if 'UREA' in siverval_df.columns:
            siverval_df.loc[i, 'UREA'] = int(siverval_df.loc[i, 'UREA'] * faktor_noise)
        if 'NPK' in siverval_df.columns:
            siverval_df.loc[i, 'NPK'] = int(siverval_df.loc[i, 'NPK'] * faktor_noise)

    # =====================================================
    # 4. SIMPAN KE EXCEL
    # =====================================================
    rdkk_path = os.path.join('dummy_data', f'data_rdkk{suffix}.xlsx')
    siverval_path = os.path.join('dummy_data', f'data_siverval{suffix}.xlsx')

    # Simpan RDKK
    rdkk_df.to_excel(rdkk_path, index=False, engine='openpyxl')

    # Simpan SIVERVAL dengan judul merged cell
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment

    wb = Workbook()
    ws = wb.active
    ws.title = "Si Verval"

    total_kolom = len(siverval_df.columns)
    last_col_letter = chr(64 + total_kolom) if total_kolom <= 26 else 'S'

    ws.merge_cells(f'A1:{last_col_letter}1')
    ws['A1'] = 'Si Verval - Kementerian Pertanian'
    ws['A1'].font = Font(bold=False, size=11)
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')

    for col_idx, col_name in enumerate(siverval_df.columns, 1):
        cell = ws.cell(row=2, column=col_idx, value=col_name)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')

    for row_idx, row in enumerate(siverval_df.values, 3):
        for col_idx, value in enumerate(row, 1):
            ws.cell(row=row_idx, column=col_idx, value=value)

    wb.save(siverval_path)

    # =====================================================
    # 5. OUTPUT
    # =====================================================
    print("=" * 60)
    print("DATA DUMMY BERHASIL DIBUAT!")
    print("=" * 60)
    print(f"\nFile tersimpan di:")
    print(f"   - {rdkk_path}")
    print(f"   - {siverval_path}")
    print(f"\nStatistik:")
    print(f"   - RDKK    : {len(rdkk_df)} petani")
    print(f"   - SIVERVAL: {len(siverval_df)} transaksi")
    print(f"\nSkenario yang di-generate:")
    print(f"   - ~35% NORMAL (tebus semua, kios sesuai)")
    print(f"   - ~30% Tidak tebus semua (selisih > 0)")
    print(f"   - ~20% Tebus melebihi pengajuan (rasio > 1)")
    print(f"   - ~15% Tebus pupuk di luar RDKK (SP36/Organik Cair)")
    print(f"   - +10  Petani tanpa pengajuan RDKK")
    print(f"   - Noise & edge case ditambahkan")

    # List semua file yang ada
    all_files = sorted(glob.glob(os.path.join('dummy_data', '*.xlsx')))
    print(f"\nSemua file di dummy_data/:")
    for f in all_files:
        print(f"   - {os.path.basename(f)}")

    print(f"\nJalankan lagi 'python generate_dummy.py' untuk generate data baru!")


if __name__ == '__main__':
    generate_dummy()