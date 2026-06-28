import logging
from config.supabase_client import get_supabase

logger = logging.getLogger(__name__)


def get_kecamatan_by_kode(kode_desa: str) -> str | None:
    """Lookup kecamatan dari kode desa BPS via tabel kecamatan_desa di Supabase."""
    try:
        supabase = get_supabase()
        result = (
            supabase.table('kecamatan_desa')
            .select('kecamatan')
            .eq('kode_desa', kode_desa)
            .limit(1)
            .execute()
        )
        if result.data and len(result.data) > 0:
            return result.data[0]['kecamatan']
        return None
    except Exception as e:
        logger.error(f"Gagal lookup kode_desa {kode_desa}: {e}")
        return None


def get_kecamatan_from_rdkk(rdkk_data: list[dict]) -> list[str]:
    """Ambil semua kecamatan unik dari data RDKK dengan lookup kode_desa.

    Args:
        rdkk_data: List of dict baris data RDKK (sudah di-parse dari Excel).

    Returns:
        List kecamatan unik yang ditemukan, kosong jika tidak ada.
    """
    # Kumpulkan kode_desa unik terlebih dahulu (hemat query)
    kode_desa_set: set[str] = set()
    for row in rdkk_data:
        row_normalized = {k.strip().lower(): v for k, v in row.items()}
        kode_desa = row_normalized.get('kode desa') or row_normalized.get('kode_desa')
        if kode_desa:
            kode_str = str(kode_desa).strip()
            if kode_str and kode_str.lower() != 'nan':
                kode_desa_set.add(kode_str)

    if not kode_desa_set:
        return []

    # Batch query semua kode_desa unik sekaligus
    try:
        supabase = get_supabase()
        result = (
            supabase.table('kecamatan_desa')
            .select('kode_desa, kecamatan')
            .in_('kode_desa', list(kode_desa_set))
            .execute()
        )
        kecamatan_map = {row['kode_desa']: row['kecamatan'] for row in (result.data or [])}
    except Exception as e:
        logger.error(f"Gagal batch lookup kode_desa: {e}")
        kecamatan_map = {}

    kecamatan_set: set[str] = set()
    for kode in kode_desa_set:
        kecamatan = kecamatan_map.get(kode)
        if kecamatan:
            normalized = str(kecamatan).strip().title()
            if not normalized.lower().startswith('kecamatan'):
                normalized = f'Kecamatan {normalized.title()}'
            kecamatan_set.add(normalized)
    return sorted(kecamatan_set)


def get_kecamatan_from_siverval(siverval_data: list[dict]) -> list[str]:
    """Ambil semua kecamatan unik dari data SIVERVAL (kolom KECAMATAN langsung).

    Args:
        siverval_data: List of dict baris data SIVERVAL (sudah di-parse dari Excel).

    Returns:
        List kecamatan unik yang ditemukan, kosong jika tidak ada.
    """
    kecamatan_set: set[str] = set()

    for row in siverval_data:
        # Case-insensitive + strip whitespace
        row_normalized = {k.strip().lower(): v for k, v in row.items()}
        val = row_normalized.get('kecamatan')
        if val and str(val).strip().lower() != 'nan':
            normalized = str(val).strip().title()
            # Standarisasi: tambahkan prefix "Kecamatan" jika belum ada
            if not normalized.lower().startswith('kecamatan'):
                normalized = f'Kecamatan {normalized}'
            kecamatan_set.add(normalized)

    return sorted(kecamatan_set)
