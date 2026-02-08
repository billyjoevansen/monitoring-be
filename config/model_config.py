"""
Konfigurasi Hyperparameter Random Forest.

Membaca dari model_config.json agar bisa diubah dari frontend.
Jika file JSON tidak ada, gunakan default.
"""
import os
import json


CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'model_config.json')

# Default config (fallback jika JSON tidak ada)
DEFAULT_CONFIG = {
    'hyperparameters': {
        'n_estimators': 200,
        'criterion': 'entropy',
        'max_depth': 10,
        'max_features': 'sqrt',
        'min_samples_split': 10,
        'min_samples_leaf': 5,
        'class_weight': 'balanced',
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

# Validasi: nilai yang diperbolehkan untuk setiap parameter
PARAM_RULES = {
    'n_estimators': {'type': int, 'min': 10, 'max': 1000},
    'criterion': {'type': str, 'choices': ['gini', 'entropy']},
    'max_depth': {'type': (int, type(None)), 'min': 1, 'max': 100},
    'max_features': {'type': (str, float, type(None)), 'choices_str': ['sqrt', 'log2']},
    'min_samples_split': {'type': int, 'min': 2, 'max': 50},
    'min_samples_leaf': {'type': int, 'min': 1, 'max': 50},
    'class_weight': {'type': (str, type(None)), 'choices_str': ['balanced']},
    'bootstrap': {'type': bool},
    'oob_score': {'type': bool},
    'random_state': {'type': (int, type(None))},
    'n_jobs': {'type': int},
    'test_size': {'type': float, 'min': 0.1, 'max': 0.5},
}


def load_config() -> dict:
    """Membaca konfigurasi dari JSON file."""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
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
                errors.append(f"{param}: tipe harus {rules['type']}, dapat {type(value).__name__}")
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

        # Cek choices
        if 'choices' in rules and isinstance(value, str):
            if value not in rules['choices']:
                errors.append(f"{param}: pilihan harus {rules['choices']}, dapat '{value}'")

    return errors


def get_random_forest_params() -> dict:
    """Mengambil hyperparameter Random Forest dari config."""
    config = load_config()
    return config.get('hyperparameters', DEFAULT_CONFIG['hyperparameters'])


def get_training_config() -> dict:
    """Mengambil konfigurasi training dari config."""
    config = load_config()
    return config.get('training_config', DEFAULT_CONFIG['training_config'])


# Backward compatibility
RANDOM_FOREST_PARAMS = get_random_forest_params()
TRAINING_CONFIG = get_training_config()