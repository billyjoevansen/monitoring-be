import io
import os
import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment

KECAMATAN_DESA = {
    'Kecamatan Walantaka': [
        ('3673011001', 'WALANTAKA'), ('3673011002', 'CIGOONG'), ('3673011003', 'KALODRAN'),
    ],
    'Kecamatan Curug': [
        ('3673011004', 'CURUG'), ('3673011005', 'CIPETE'), ('3673011006', 'CURUG MANIS'),
    ],
    'Kecamatan Cipocok Jaya': [
        ('3673011007', 'BANJARSARI'), ('3673011008', 'DALUNG'), ('3673011009', 'GELAM'),
    ],
    'Kecamatan Kasemen': [
        ('3673011010', 'KASEMEN'), ('3673011011', 'BANTEN'), ('3673011012', 'BENDUNG'),
    ],
    'Kecamatan Taktakan': [
        ('3673011013', 'TAKTAKAN'), ('3673011014', 'CILOWONG'), ('3673011015', 'DRANGONG'),
    ],
    'Kecamatan Serang': [
        ('3673011016', 'SERANG'), ('3673011017', 'CIPARE'), ('3673011018', 'KOTA BARU'),
    ],
}

NAMA_DEPAN = [
    'Budi', 'Siti', 'Ahmad', 'Dewi', 'Agus', 'Sri', 'Hadi', 'Rina',
    'Joko', 'Ani', 'Wahyu', 'Lestari', 'Bambang', 'Nurma', 'Eko',
    'Yanti', 'Dani', 'Wati', 'Rudi', 'Mega', 'Andi', 'Asep', 'Cecep',
    'Dedi', 'Eneng', 'Fajar', 'Gita', 'Hendra', 'Indra', 'Iwan',
    'Kartika', 'Mulyadi', 'Nana', 'Oki', 'Putri', 'Rahmat', 'Soleh',
    'Taufik', 'Ujang', 'Yanto', 'Zaki', 'Fitria', 'Rizky', 'Dewantara',
    'Sari', 'Wibowo', 'Yusuf', 'Zainal', 'Fadli', 'Guntur',
]

NAMA_BELAKANG = [
    'Santoso', 'Wijaya', 'Hartono', 'Susanto', 'Rahayu', 'Pratama',
    'Saputra', 'Handayani', 'Kusuma', 'Hidayat', 'Lestari', 'Cahyono',
    'Setiawan', 'Purnama', 'Nugroho', 'Wulandari', 'Suryadi', 'Utami',
    'Mulyana', 'Sudarsono', 'Gunawan', 'Suhendar', 'Heryanto', 'Fauzi',
    'Ardiansyah', 'Siregar', 'Laksana', 'Kurniawan', 'Basri', 'Mahendra',
]

PENYULUH_LIST = [
    'PUTRI KEMALA DEWI, S.P', 'DR. IR. H. AHMAD SUHENDAR, M.P',
    'SITI NURJANAH, S.P', 'BAMBANG Setiawan, S.Pt',
    'RINA WIDIASTUTI, S.P', 'EKO PRASETYO, S.P',
]

POKTAN_LIST = [
    'Sri Rejeki', 'Tani Mulyo', 'Karya Tani', 'Maju Jaya', 'Sawit Berkah',
    'Harapan Baru', 'Mekar Sari', 'Subur Makmur', 'Berkah Tani',
    'Sinar Jaya', 'Menteng Jaya', 'Sinar Melati', 'Mina Mukti',
    'Sumber Jaya', 'Setia Kawan', 'Taruna Mekar', 'Bina Tani',
    'Tani Rahayu', 'Sida Mukti', 'Maju Bersama', 'Tani Mandiri',
    'Hurip', 'Mutiara Tani', 'Cipta Karya', 'Tunas Harapan',
    'Sari Bumi', 'Agro Lestari', 'Tani Sejahtera', 'IKHLAS TANI SEJAHTERA',
]

KOMODITAS_LIST = ['CABAI', 'JAGUNG', 'PADI', 'UBI KAYU']
SUPSEKTOR_LIST = ['HORTIKULTURA', 'TANAMAN PANGAN']
KODE_KIOS = 'RT0000003780'
NAMA_KIOS = 'PUSAKA TANI I'


def _generate_nik(rng: np.random.Generator) -> str:
    return f'`36{"".join([str(rng.integers(0, 10)) for _ in range(14)])}'


def _generate_nik_siverval(rng: np.random.Generator) -> str:
    return f"'36{"".join([str(rng.integers(0, 10)) for _ in range(14)])}"


def _get_desa(kecamatan_filter: str | None):
    if kecamatan_filter:
        desa_list = KECAMATAN_DESA.get(kecamatan_filter, [])
        if not desa_list:
            raise ValueError(f"Kecamatan '{kecamatan_filter}' tidak ditemukan")
        return desa_list
    all_desa = []
    for desas in KECAMATAN_DESA.values():
        all_desa.extend(desas)
    return all_desa


def generate_dummy_data(
    n_petani: int = 350,
    n_transaksi: int = 260,
    seed: int | None = None,
    pct_normal: float = 35,
    pct_over: float = 20,
    pct_luar_rdkk: float = 15,
    pct_kurang: float = 15,
    pct_tanpa_pengajuan: float = 10,
    pct_nonaktif: float = 5,
    kecamatan_filter: str | None = None,
):
    if abs(pct_normal + pct_over + pct_luar_rdkk + pct_kurang + pct_tanpa_pengajuan + pct_nonaktif - 100) > 0.01:
        raise ValueError('Persentase skenario harus berjumlah 100%')

    rng = np.random.default_rng(seed)
    seed_val = seed if seed is not None else rng.integers(0, 2**31)
    np.random.seed(seed_val)

    all_desa = _get_desa(kecamatan_filter)
    petani_kode_desa = []
    petani_nama_desa = []
    petani_kecamatan = []

    for _ in range(n_petani):
        kd, nd = all_desa[rng.integers(0, len(all_desa))]
        petani_kode_desa.append(kd)
        petani_nama_desa.append(nd)
        if kecamatan_filter:
            kec = kecamatan_filter.replace('Kecamatan ', '')
            petani_kecamatan.append(kec)
        else:
            for kec_name, desas in KECAMATAN_DESA.items():
                if (kd, nd) in desas:
                    petani_kecamatan.append(kec_name.replace('Kecamatan ', ''))
                    break

    niks = [_generate_nik(rng) for _ in range(n_petani)]
    nama_petani = [
        f'{rng.choice(NAMA_DEPAN)} {rng.choice(NAMA_BELAKANG)}'
        for _ in range(n_petani)
    ]
    tempat_lahir = ['SERANG', 'LEBAK', 'CILEGON', 'PANDEGLANG', 'TANGERANG', 'JAKARTA', 'BANDUNG']

    rdkk = {
        'Nama Penyuluh': [str(rng.choice(PENYULUH_LIST)) for _ in range(n_petani)],
        'Kode Desa': petani_kode_desa,
        'Kode Kios Pengecer': [KODE_KIOS] * n_petani,
        'Nama Kios Pengecer': [NAMA_KIOS] * n_petani,
        'Gapoktan': [None] * n_petani,
        'Nama Poktan': [str(rng.choice(POKTAN_LIST)) for _ in range(n_petani)],
        'Nama Petani': nama_petani,
        'KTP': niks,
        'Tempat Lahir': [str(rng.choice(tempat_lahir)) for _ in range(n_petani)],
        'Tanggal Lahir': [
            f'{rng.integers(1960, 1995)}-{rng.integers(1, 13):02d}-{rng.integers(1, 29):02d}'
            for _ in range(n_petani)
        ],
        'Nama Ibu Kandung': [
            f'{rng.choice(NAMA_DEPAN)} {rng.choice(NAMA_BELAKANG)}'
            for _ in range(n_petani)
        ],
        'Alamat': [
            f'PERUMNAS CIRACAS INDAH BLOK C3 NO {rng.integers(1, 200)} RT{rng.integers(1, 12):02d}/12 SERANG'
            for _ in range(n_petani)
        ],
        'Subsektor': [str(rng.choice(SUPSEKTOR_LIST)) for _ in range(n_petani)],
        'Komoditas MT1': [str(rng.choice(KOMODITAS_LIST)) for _ in range(n_petani)],
        'Luas Lahan (Ha) MT1': list(np.round(rng.uniform(0.1, 2.0, n_petani), 2)),
        'Pupuk Urea (Kg) MT1': list(rng.choice([50, 80, 100, 120, 150, 200, 250, 300, 400, 500], n_petani).astype(int)),
        'Pupuk NPK (Kg) MT1': list(rng.choice([50, 80, 100, 120, 150, 180, 200, 250, 300, 400, 480, 600], n_petani).astype(int)),
        'Pupuk NPK Formula (Kg) MT1': [None] * n_petani,
        'Pupuk Organik (Kg) MT1': [None] * n_petani,
        'Pupuk ZA (Kg) MT1': [None] * n_petani,
        'Komoditas MT2': [str(rng.choice(KOMODITAS_LIST)) if rng.random() < 0.90 else '' for _ in range(n_petani)],
        'Luas Lahan (Ha) MT2': [round(rng.uniform(0.1, 1.5), 2) if rng.random() < 0.90 else 0.0 for _ in range(n_petani)],
        'Pupuk Urea (Kg) MT2': [int(rng.choice([50, 80, 100, 120, 150, 200])) if rng.random() < 0.90 else None for _ in range(n_petani)],
        'Pupuk NPK (Kg) MT2': [int(rng.choice([50, 80, 100, 120, 150, 200, 250])) if rng.random() < 0.90 else None for _ in range(n_petani)],
        'Pupuk NPK Formula (Kg) MT2': [None] * n_petani,
        'Pupuk Organik (Kg) MT2': [None] * n_petani,
        'Pupuk ZA (Kg) MT2': [None] * n_petani,
        'Komoditas MT3': [''] * n_petani,
        'Luas Lahan (Ha) MT3': [0.0] * n_petani,
        'Pupuk Urea (Kg) MT3': [None] * n_petani,
        'Pupuk NPK (Kg) MT3': [None] * n_petani,
        'Pupuk NPK Formula (Kg) MT3': [None] * n_petani,
        'Pupuk Organik (Kg) MT3': [None] * n_petani,
        'Pupuk ZA (Kg) MT3': [None] * n_petani,
    }

    rdkk_df = pd.DataFrame(rdkk)

    petani_transaksi_idx = rng.choice(n_petani, min(n_transaksi, n_petani), replace=False).tolist()
    if n_transaksi > n_petani:
        extra = rng.choice(n_petani, n_transaksi - n_petani, replace=True).tolist()
        petani_transaksi_idx.extend(extra)

    weights = np.array([
        pct_normal, pct_over, pct_luar_rdkk,
        pct_kurang, pct_tanpa_pengajuan, pct_nonaktif,
    ]) / 100.0

    scenario_assignments = rng.choice(6, size=len(petani_transaksi_idx), p=weights).tolist()
    scenario_map = {
        0: 'normal',
        1: 'over',
        2: 'luar_rdkk',
        3: 'kurang',
        4: 'tanpa_pengajuan',
        5: 'nonaktif',
    }

    siverval_records = []
    for no, (idx, sc_key) in enumerate(zip(petani_transaksi_idx, scenario_assignments), 1):
        scenario = scenario_map[sc_key]
        nik_rdkk = niks[idx]
        nik_sv = "'" + nik_rdkk[1:]
        nama = nama_petani[idx]

        urea_total = int(rdkk['Pupuk Urea (Kg) MT1'][idx] or 0) + int(rdkk['Pupuk Urea (Kg) MT2'][idx] or 0)
        npk_total = int(rdkk['Pupuk NPK (Kg) MT1'][idx] or 0) + int(rdkk['Pupuk NPK (Kg) MT2'][idx] or 0)

        if scenario == 'normal':
            urea_tebus = urea_total
            npk_tebus = npk_total
            sp36 = 0
            organik_cair = 0
            status = 'Disetujui Tim Verval Pusat'

        elif scenario == 'over':
            urea_tebus = int(urea_total * rng.uniform(1.1, 2.0))
            npk_tebus = int(npk_total * rng.uniform(1.0, 1.5))
            sp36 = 0
            organik_cair = 0
            status = 'Disetujui Tim Verval Pusat'

        elif scenario == 'luar_rdkk':
            urea_tebus = int(urea_total * rng.uniform(0.8, 1.0))
            npk_tebus = int(npk_total * rng.uniform(0.8, 1.0))
            sp36 = int(rng.choice([50, 100, 150]))
            organik_cair = int(rng.choice([0, 20, 50]))
            status = 'Disetujui Tim Verval Pusat'

        elif scenario == 'kurang':
            urea_tebus = int(urea_total * rng.uniform(0.1, 0.84))
            npk_tebus = int(npk_total * rng.uniform(0.1, 0.84))
            sp36 = 0
            organik_cair = 0
            status = 'Disetujui Tim Verval Pusat'

        elif scenario == 'tanpa_pengajuan':
            urea_tebus = int(rng.choice([50, 100, 150]))
            npk_tebus = int(rng.choice([50, 100, 150]))
            sp36 = 0
            organik_cair = 0
            status = 'Disetujui Tim Verval Pusat'

        elif scenario == 'nonaktif':
            urea_tebus = int(urea_total * rng.uniform(0.5, 1.0))
            npk_tebus = int(npk_total * rng.uniform(0.5, 1.0))
            sp36 = 0
            organik_cair = 0
            status = 'Non-aktif'

        no_transaksi = f'S02KA1\\{rng.choice(["V", "W"])}00{rng.choice(["X", "Y", "Z", "U"])}{chr(86 + no % 26)}'
        tgl_tebus = f'{rng.integers(1, 29)}-{rng.integers(1, 7)}-2026'
        tgl_input = f'2026-{rng.integers(1, 7):02d}-{rng.integers(1, 29):02d} {rng.integers(8, 18):02d}:{rng.integers(0, 60):02d}:00'

        siverval_records.append({
            'NO': no,
            'KABUPATEN': 'KOTA SERANG',
            'KECAMATAN': petani_kecamatan[idx] if idx < len(petani_kecamatan) else 'SERANG',
            'NO TRANSAKSI': no_transaksi,
            'KODE KIOS': KODE_KIOS,
            'NAMA KIOS': NAMA_KIOS,
            'NIK': nik_sv,
            'NAMA PETANI': nama,
            'UREA': urea_tebus,
            'NPK': npk_tebus,
            'SP36': sp36,
            'ZA': 0,
            'NPK FORMULA': 0,
            'ORGANIK': 0,
            'ORGANIK CAIR': organik_cair,
            'TGL TEBUS': tgl_tebus,
            'TGL INPUT': tgl_input,
            'STATUS': status,
        })

    siverval_df = pd.DataFrame(siverval_records)

    rdkk_buf = io.BytesIO()
    rdkk_df.to_excel(rdkk_buf, index=False, engine='openpyxl')
    rdkk_buf.seek(0)

    siverval_buf = io.BytesIO()
    wb = Workbook()
    ws = wb.active
    ws.title = 'Si Verval'

    total_kolom = len(siverval_df.columns)
    last_col = chr(64 + total_kolom) if total_kolom <= 26 else 'S'
    ws.merge_cells(f'A1:{last_col}1')
    ws['A1'] = 'Si Verval - Kementrian Pertanian'
    ws['A1'].font = Font(bold=False, size=11)
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')

    for col_idx, col_name in enumerate(siverval_df.columns, 1):
        cell = ws.cell(row=2, column=col_idx, value=col_name)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')

    for row_idx, row in enumerate(siverval_df.values, 3):
        for col_idx, value in enumerate(row, 1):
            ws.cell(row=row_idx, column=col_idx, value=value)

    wb.save(siverval_buf)
    siverval_buf.seek(0)

    label_counts = pd.Series(scenario_assignments).map(scenario_map).value_counts()
    summary = {
        'n_petani': n_petani,
        'n_transaksi': len(petani_transaksi_idx),
        'seed': int(seed_val),
        'kecamatan': kecamatan_filter or 'Semua',
        'distribusi_skenario': {str(k): int(v) for k, v in label_counts.to_dict().items()},
    }

    return rdkk_buf, siverval_buf, summary
