import os
import logging
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import (
    train_test_split,
    StratifiedKFold,
    ParameterGrid,
    cross_val_score,
)
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

    # =====================================================
    # SPLIT DATA (robust terhadap class imbalance)
    # =====================================================
    min_class_count = y.value_counts().min()
    test_size = TRAIN_CONFIG['test_size']

    if min_class_count < 4:
        # Manual split: semua minoritas ke training, split hanya majority
        logger.info(
            f"Kelas minoritas hanya {min_class_count} sampel. "
            f"Menggunakan manual split agar semua minoritas masuk training."
        )
        class_counts = y.value_counts()
        majority_class = class_counts.idxmax()
        minority_class = class_counts.idxmin()

        minority_idx = y[y == minority_class].index
        majority_idx = y[y == majority_class].index

        maj_train, maj_test = train_test_split(
            majority_idx,
            test_size=test_size,
            random_state=TRAIN_CONFIG['random_state'],
        )

        train_idx = maj_train.union(minority_idx)
        test_idx = maj_test

        X_train, X_test = X.loc[train_idx], X.loc[test_idx]
        y_train, y_test = y.loc[train_idx], y.loc[test_idx]
    else:
        # Stratified split normal
        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=test_size,
            random_state=TRAIN_CONFIG['random_state'],
            stratify=y,
        )

    # Validasi setelah split
    train_classes = y_train.unique()
    if len(train_classes) < 2:
        class_counts = y.value_counts().to_dict()
        class_desc = ', '.join(f"{k}: {v}" for k, v in class_counts.items())
        raise ValueError(
            f"Setelah split, data training hanya memiliki 1 kelas. "
            f"Distribusi label asli: {class_desc}. "
            f"Tambahkan data untuk kelas yang kurang (minimal 4 sampel per kelas)."
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
    from datetime import datetime, timezone
    model_data = {
        'model': model,
        'features': selected_features,
        'params': RF_PARAMS,
        'metrics': {
            'accuracy':          round(accuracy, 4),
            'f1_score_weighted': round(f1_weighted, 4),
            'oob_score':         round(model.oob_score_, 4) if RF_PARAMS['oob_score'] else None,
        },
        'trained_at': datetime.now(timezone.utc).isoformat(),
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


def tune_and_train(df: pd.DataFrame) -> dict:
    """
    Hyperparameter tuning dengan 10-Fold Stratified CV + Grid Search.
    Mengembalikan model terbaik beserta hasil CV.
    """
    RF_PARAMS = get_random_forest_params()
    TRAIN_CONFIG = get_training_config()

    os.makedirs(MODEL_DIR, exist_ok=True)

    # Siapkan fitur dan label
    available_features = [col for col in FEATURE_COLUMNS if col in df.columns]
    X = df[available_features].fillna(0)
    y = df['label']

    # Validasi
    if len(X) < 10:
        raise ValueError(f"Data terlalu sedikit untuk training: {len(X)} baris. Minimal 10 baris.")

    unique_labels = y.unique()
    if len(unique_labels) < 2:
        label_name = 'NORMAL' if 0 in unique_labels else 'TIDAK NORMAL'
        raise ValueError(
            f"Data hanya memiliki 1 kelas: {label_name}. "
            f"Dibutuhkan minimal 2 kelas untuk training."
        )

    # =====================================================
    # FEATURE SELECTION (dengan model awal)
    # =====================================================
    initial_model = RandomForestClassifier(
        n_estimators=50,
        criterion=RF_PARAMS['criterion'],
        max_depth=RF_PARAMS['max_depth'],
        class_weight=RF_PARAMS['class_weight'],
        random_state=RF_PARAMS['random_state'],
        n_jobs=RF_PARAMS['n_jobs'],
    )
    initial_model.fit(X, y)

    selector = SelectFromModel(initial_model, threshold='median')
    selector.fit(X, y)

    selected_mask = selector.get_support()
    selected_features = [f for f, s in zip(available_features, selected_mask) if s]
    dropped_features = [f for f, s in zip(available_features, selected_mask) if not s]

    if len(selected_features) < 3:
        selected_features = available_features
        dropped_features = []

    X_selected = X[selected_features]

    # =====================================================
    # HYPERPARAMETER GRID
    # =====================================================
    param_grid = {
        'n_estimators': [100, 200, 500],
        'max_depth': [5, 10, 20, None],
        'min_samples_split': [10, 20],
        'min_samples_leaf': [5, 10, 20],
    }

    n_combinations = 1
    for v in param_grid.values():
        n_combinations *= len(v)

    logger.info(f"Hyperparameter tuning: {n_combinations} kombinasi x 10 fold = {n_combinations * 10} training runs")

    # =====================================================
    # 10-FOLD STRATIFIED CV + GRID SEARCH
    # =====================================================
    cv = StratifiedKFold(n_splits=10, shuffle=True, random_state=42)

    best_score = 0.0
    best_params = {}
    cv_results = []

    for i, params in enumerate(ParameterGrid(param_grid)):
        model = RandomForestClassifier(
            **params,
            criterion=RF_PARAMS['criterion'],
            max_features=RF_PARAMS['max_features'],
            class_weight=RF_PARAMS['class_weight'],
            bootstrap=True,
            oob_score=False,
            random_state=42,
            n_jobs=-1,
        )

        scores = cross_val_score(
            model, X_selected, y,
            cv=cv,
            scoring='f1_weighted',
            n_jobs=-1,
        )

        mean_f1 = float(scores.mean())
        std_f1 = float(scores.std())

        cv_results.append({
            'rank': 0,
            'params': params,
            'mean_f1': round(mean_f1, 4),
            'std_f1': round(std_f1, 4),
            'fold_scores': [round(float(s), 4) for s in scores],
        })

        if mean_f1 > best_score:
            best_score = mean_f1
            best_params = params

        if (i + 1) % 10 == 0:
            logger.info(f"Progress: {i + 1}/{n_combinations} kombinasi selesai")

    # Ranking
    cv_results.sort(key=lambda x: x['mean_f1'], reverse=True)
    for rank, item in enumerate(cv_results, 1):
        item['rank'] = rank

    logger.info(f"Best CV F1: {best_score:.4f} | Params: {best_params}")

    # =====================================================
    # TRAIN MODEL FINAL dengan best_params + seluruh data
    # =====================================================
    final_model = RandomForestClassifier(
        **best_params,
        criterion=RF_PARAMS['criterion'],
        max_features=RF_PARAMS['max_features'],
        class_weight=RF_PARAMS['class_weight'],
        bootstrap=True,
        oob_score=True,
        random_state=42,
        n_jobs=-1,
    )
    final_model.fit(X_selected, y)

    # Feature importance dari model final
    feature_importance = dict(zip(selected_features, final_model.feature_importances_.tolist()))
    feature_importance = dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True))

    oob = round(final_model.oob_score_, 4) if final_model.oob_score_ else None

    # =====================================================
    # EVALUASI MODEL FINAL (full data untuk confusion matrix)
    # =====================================================
    y_pred = final_model.predict(X_selected)
    accuracy = accuracy_score(y, y_pred)
    f1_weighted = f1_score(y, y_pred, average='weighted', labels=[0, 1], zero_division=0)
    cm = confusion_matrix(y, y_pred, labels=[0, 1])

    report = classification_report(
        y, y_pred,
        labels=[0, 1],
        target_names=['NORMAL', 'TIDAK_NORMAL'],
        output_dict=True,
        zero_division=0,
    )

    # =====================================================
    # SIMPAN MODEL
    # =====================================================
    from datetime import datetime, timezone
    model_data = {
        'model': final_model,
        'features': selected_features,
        'params': best_params,
        'metrics': {
            'accuracy': round(accuracy, 4),
            'f1_score_weighted': round(f1_weighted, 4),
            'oob_score': oob,
        },
        'trained_at': datetime.now(timezone.utc).isoformat(),
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
        'tuning': {
            'method': 'GridSearchCV + 10-Fold StratifiedKFold',
            'n_folds': 10,
            'total_combinations': n_combinations,
            'best_params': best_params,
            'best_cv_f1': round(best_score, 4),
            'cv_results': cv_results[:20],
        },
        'model_config': {
            'algorithm': 'RandomForestClassifier',
            'hyperparameters': best_params,
            'training_config': TRAIN_CONFIG,
            'total_data': len(X),
            'features_used': selected_features,
        },
        'model_file': {
            'path': MODEL_PATH,
            'size_kb': pkl_size_kb,
        },
        'label_distribution': {},
        'message': 'Model berhasil dilatih dengan hyperparameter tuning (10-Fold CV).',
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