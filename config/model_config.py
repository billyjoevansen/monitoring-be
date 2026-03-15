"""
Konfigurasi Hyperparameter Random Forest.

Membaca dari model_config.json agar bisa diubah dari frontend.
Jika file JSON tidak ada, gunakan default.
"""
import os
import json
import logging

logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'model_config.json')

# Default config (fallback jika JSON tidak ada)
# FIX 2: Diselaraskan dengan model_config.json (gini, balanced_subsample, 400 estimator)
DEFAULT_CONFIG = {
    'hyperparameters': {
        'n_estimators': 400,
        'criterion': 'gini',
        'max_depth': 15,
        'max_features': 'sqrt',
        'min_samples_split': 10,
        'min_samples_leaf': 5,
        'class_weight': 'balanced_subsample',
        'bootstrap': True,
        'oob_score': True,
        'random_state': 42,
        'n_jobs': -1,
    },
    'training_config': {
        'test_size': 0.2,
        'random_state': 42,
        'stratify': True,
    }
}

# FIX 3: choices_str diganti choices agar benar-benar divalidasi
# Tambahkan 'balanced_subsample' karena itu yang dipakai di JSON
PARAM_RULES = {
    'n_estimators':      {'type': int,               'min': 10,  'max': 1000},
    'criterion':         {'type': str,               'choices': ['gini', 'entropy']},
    'max_depth':         {'type': (int, type(None)), 'min': 1,   'max': 100},
    'max_features':      {'type': (str, float, type(None)), 'choices': ['sqrt', 'log2']},
    'min_samples_split': {'type': int,               'min': 2,   'max': 50},
    'min_samples_leaf':  {'type': int,               'min': 1,   'max': 50},
    'class_weight':      {'type': (str, type(None)), 'choices': ['balanced', 'balanced_subsample']},
    'bootstrap':         {'type': bool},
    'oob_score':         {'type': bool},
    'random_state':      {'type': (int, type(None))},
    'n_jobs':            {'type': int},
    'test_size':         {'type': float,             'min': 0.1, 'max': 0.5},
}


def load_config() -> dict:
    """
    Membaca konfigurasi dari JSON file.
    FIX 4: Tangkap error jika JSON corrupt agar app tidak crash saat startup.
    """
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(
                f'model_config.json tidak bisa dibaca ({e}), '
                f'menggunakan DEFAULT_CONFIG sebagai fallback.'
            )
    return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> None:
    """Menyimpan konfigurasi ke JSON file."""
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=4)


def validate_config(config: dict) -> list:
    """
    Validasi konfigurasi yang dikirim dari frontend.
    Returns list of error messages (kosong jika valid).
    """
    errors = []

    hp = config.get('hyperparameters', {})
    tc = config.get('training_config', {})
    all_params = {**hp, **tc}

    for param, value in all_params.items():
        if param not in PARAM_RULES:
            continue

        rules = PARAM_RULES[param]

        # Cek type
        if not isinstance(value, rules['type']):
            if value is not None:
                errors.append(
                    f"{param}: tipe harus {rules['type']}, dapat {type(value).__name__}"
                )
                continue

        if value is None:
            continue

        # Cek min/max
        if 'min' in rules and isinstance(value, (int, float)):
            if value < rules['min']:
                errors.append(f"{param}: nilai minimum {rules['min']}, dapat {value}")
        if 'max' in rules and isinstance(value, (int, float)):
            if value > rules['max']:
                errors.append(f"{param}: nilai maksimum {rules['max']}, dapat {value}")

        # FIX 3: Sekarang 'choices' dipakai konsisten untuk semua string parameter
        if 'choices' in rules and isinstance(value, str):
            if value not in rules['choices']:
                errors.append(
                    f"{param}: pilihan harus {rules['choices']}, dapat '{value}'"
                )

    return errors


def get_random_forest_params() -> dict:
    """Mengambil hyperparameter Random Forest dari config."""
    config = load_config()
    return config.get('hyperparameters', DEFAULT_CONFIG['hyperparameters'])


def get_training_config() -> dict:
    """Mengambil konfigurasi training dari config."""
    config = load_config()
    return config.get('training_config', DEFAULT_CONFIG['training_config'])


# FIX 1: Hapus eksekusi di module level — dipindah ke lazy load via fungsi di atas.
# Dulu: RANDOM_FOREST_PARAMS = get_random_forest_params()  ← crash jika JSON corrupt
# Sekarang: panggil get_random_forest_params() langsung saat dibutuhkan di prediction.py