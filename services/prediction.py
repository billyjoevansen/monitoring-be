import os
import logging
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.feature_selection import SelectFromModel
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from services.preprocessing import FEATURE_COLUMNS
from config.model_config import get_random_forest_params, get_training_config

logger = logging.getLogger(__name__)


MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')
MODEL_PATH = os.path.join(MODEL_DIR, 'random_forest.pkl')


def train_model(df: pd.DataFrame) -> dict:
    """
    Melatih model Random Forest dengan Feature Selection otomatis.
    """
    RF_PARAMS = get_random_forest_params()
    TRAIN_CONFIG = get_training_config()

    os.makedirs(MODEL_DIR, exist_ok=True)

    # Siapkan fitur dan label
    available_features = [col for col in FEATURE_COLUMNS if col in df.columns]
    X = df[available_features].fillna(0)
    y = df['label']

    # =====================================================
    # VALIDASI DATA
    # =====================================================
    if len(X) < 10:
        raise ValueError(
            f"Data terlalu sedikit untuk training: {len(X)} baris. "
            f"Minimal 10 baris."
        )

    unique_labels = y.unique()
    if len(unique_labels) < 2:
        label_name = 'NORMAL' if 0 in unique_labels else 'TIDAK NORMAL'
        raise ValueError(
            f"Data hanya memiliki 1 kelas: {label_name}. "
            f"Dibutuhkan minimal 2 kelas (NORMAL & TIDAK NORMAL) untuk training. "
            f"Coba gunakan data yang lebih banyak (minimal 50 petani)."
        )

    # Cek apakah cukup data per kelas untuk stratified split
    min_class_count = y.value_counts().min()
    test_size = TRAIN_CONFIG['test_size']
    min_test_samples = max(2, int(len(X) * test_size))

    use_stratify = TRAIN_CONFIG['stratify'] and min_class_count >= 2
    if not use_stratify and TRAIN_CONFIG['stratify']:
        logger.warning(f"⚠️ Stratify dinonaktifkan karena kelas minoritas hanya {min_class_count} sampel.")

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=test_size,
        random_state=TRAIN_CONFIG['random_state'],
        stratify=y if use_stratify else None,
    )

    # Validasi setelah split
    if len(y_train.unique()) < 2:
        raise ValueError(
            f"Setelah split, data training hanya memiliki 1 kelas. "
            f"Tambahkan lebih banyak data agar kedua kelas terwakili."
        )

    # =====================================================
    # STEP 1: Feature Selection
    # =====================================================
    initial_model = RandomForestClassifier(
        n_estimators=50,
        criterion=RF_PARAMS['criterion'],
        max_depth=RF_PARAMS['max_depth'],
        class_weight=RF_PARAMS['class_weight'],
        random_state=RF_PARAMS['random_state'],
        n_jobs=RF_PARAMS['n_jobs'],
    )
    initial_model.fit(X_train, y_train)

    selector = SelectFromModel(initial_model, threshold='median')
    selector.fit(X_train, y_train)

    selected_mask = selector.get_support()
    selected_features = [f for f, s in zip(available_features, selected_mask) if s]
    dropped_features = [f for f, s in zip(available_features, selected_mask) if not s]

    # Minimal 3 fitur terpilih
    if len(selected_features) < 3:
        selected_features = available_features
        dropped_features = []

    X_train_selected = X_train[selected_features]
    X_test_selected = X_test[selected_features]

    # =====================================================
    # STEP 2: Training Final
    # =====================================================
    model = RandomForestClassifier(
        n_estimators=RF_PARAMS['n_estimators'],
        criterion=RF_PARAMS['criterion'],
        max_depth=RF_PARAMS['max_depth'],
        max_features=RF_PARAMS['max_features'],
        min_samples_split=RF_PARAMS['min_samples_split'],
        min_samples_leaf=RF_PARAMS['min_samples_leaf'],
        class_weight=RF_PARAMS['class_weight'],
        bootstrap=RF_PARAMS['bootstrap'],
        oob_score=RF_PARAMS['oob_score'],
        random_state=RF_PARAMS['random_state'],
        n_jobs=RF_PARAMS['n_jobs'],
    )
    model.fit(X_train_selected, y_train)

    # Prediksi
    y_pred = model.predict(X_test_selected)

    # =====================================================
    # METRIK EVALUASI (dengan labels parameter agar aman)
    # =====================================================
    accuracy = accuracy_score(y_test, y_pred)
    f1_weighted = f1_score(y_test, y_pred, average='weighted', labels=[0, 1], zero_division=0)
    cm = confusion_matrix(y_test, y_pred, labels=[0, 1])

    report = classification_report(
        y_test, y_pred,
        labels=[0, 1],
        target_names=['NORMAL', 'TIDAK_NORMAL'],
        output_dict=True,
        zero_division=0,
    )

    # Feature Importance
    feature_importance = dict(zip(selected_features, model.feature_importances_.tolist()))
    feature_importance = dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True))

    # OOB Score
    oob = round(model.oob_score_, 4) if RF_PARAMS['oob_score'] else None

    # =====================================================
    # SIMPAN MODEL
    # =====================================================
    model_data = {
        'model': model,
        'features': selected_features,
        'params': RF_PARAMS,
    }
    joblib.dump(model_data, MODEL_PATH, compress=3)

    pkl_size = os.path.getsize(MODEL_PATH)
    pkl_size_kb = round(pkl_size / 1024, 2)

    return {
        'model_performance': {
            'accuracy': round(accuracy, 4),
            'f1_score_weighted': round(f1_weighted, 4),
            'oob_score': oob,
            'classification_report': {
                'NORMAL': {
                    'precision': round(report['NORMAL']['precision'], 4),
                    'recall': round(report['NORMAL']['recall'], 4),
                    'f1_score': round(report['NORMAL']['f1-score'], 4),
                    'support': int(report['NORMAL']['support']),
                },
                'TIDAK_NORMAL': {
                    'precision': round(report['TIDAK_NORMAL']['precision'], 4),
                    'recall': round(report['TIDAK_NORMAL']['recall'], 4),
                    'f1_score': round(report['TIDAK_NORMAL']['f1-score'], 4),
                    'support': int(report['TIDAK_NORMAL']['support']),
                },
            },
            'confusion_matrix': {
                'labels': ['NORMAL', 'TIDAK_NORMAL'],
                'matrix': cm.tolist(),
                'penjelasan': {
                    'true_negative': int(cm[0][0]),
                    'false_positive': int(cm[0][1]),
                    'false_negative': int(cm[1][0]),
                    'true_positive': int(cm[1][1]),
                    'keterangan': {
                        'true_negative': 'Petani NORMAL yang diprediksi NORMAL (benar)',
                        'false_positive': 'Petani NORMAL yang diprediksi TIDAK NORMAL (salah alarm)',
                        'false_negative': 'Petani TIDAK NORMAL yang diprediksi NORMAL (lolos deteksi)',
                        'true_positive': 'Petani TIDAK NORMAL yang diprediksi TIDAK NORMAL (tertangkap)',
                    }
                }
            },
            'feature_importance': feature_importance,
        },
        'feature_selection': {
            'total_fitur_awal': len(available_features),
            'total_fitur_terpilih': len(selected_features),
            'fitur_terpilih': selected_features,
            'fitur_dibuang': dropped_features,
        },
        'model_config': {
            'algorithm': 'RandomForestClassifier',
            'hyperparameters': RF_PARAMS,
            'training_config': TRAIN_CONFIG,
            'total_training_data': len(X_train),
            'total_test_data': len(X_test),
            'features_used': selected_features,
        },
        'model_file': {
            'path': MODEL_PATH,
            'size_kb': pkl_size_kb,
        },
        'message': 'Model berhasil dilatih dan disimpan.',
    }


def load_model():
    """Memuat model yang sudah disimpan."""
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            "Model belum dilatih. Silakan panggil /api/train terlebih dahulu."
        )
    return joblib.load(MODEL_PATH)


def predict(df: pd.DataFrame) -> pd.DataFrame:
    """Melakukan prediksi pada data baru."""
    model_data = load_model()
    model = model_data['model']
    features = model_data['features']

    X = df.copy()
    for col in features:
        if col not in X.columns:
            X[col] = 0

    X = X[features].fillna(0)

    predictions = model.predict(X)
    probabilities = model.predict_proba(X)

    df = df.copy()
    df['prediksi'] = predictions
    df['prediksi_label'] = df['prediksi'].map({0: 'NORMAL', 1: 'TIDAK NORMAL'})
    df['confidence'] = [
        round(float(probabilities[i][pred]), 4)
        for i, pred in enumerate(predictions)
    ]

    return df