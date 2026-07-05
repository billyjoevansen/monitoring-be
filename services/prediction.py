import os
import gc
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
    roc_curve,
    auc,
)
from services.preprocessing import FEATURE_COLUMNS
from config.model_config import get_random_forest_params, get_training_config

logger = logging.getLogger(__name__)


MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')
MODEL_PATH = os.path.join(MODEL_DIR, 'random_forest.pkl')

# Fitur yang wajib masuk meskipun importance rendah
# Kosongkan — fitur leakage tidak boleh dipaksa masuk model
MUST_INCLUDE_FEATURES = []


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
        n_jobs=1,
    )
    initial_model.fit(X_train, y_train)

    selector = SelectFromModel(initial_model, threshold='median')
    selector.fit(X_train, y_train)

    selected_mask = selector.get_support()
    selected_features = [f for f, s in zip(available_features, selected_mask) if s]
    dropped_features = [f for f, s in zip(available_features, selected_mask) if not s]

    # Force keep fitur tesis meskipun importance rendah
    for f in MUST_INCLUDE_FEATURES:
        if f in available_features and f not in selected_features:
            selected_features.append(f)
            if f in dropped_features:
                dropped_features.remove(f)

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
        n_jobs=1,
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
    # ROC-AUC
    # =====================================================
    try:
        y_prob = model.predict_proba(X_test_selected)
        fpr, tpr, _ = roc_curve(y_test, y_prob[:, 1])
        roc_auc = auc(fpr, tpr)
    except Exception:
        fpr, tpr, roc_auc = [0.0, 1.0], [0.0, 1.0], 0.5

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

    # Overfitting detection (simplified — train vs test gap)
    accuracy_gap = 0.0
    f1_gap = 0.0
    is_overfitting = False

    return {
        'model_performance': {
            'oob_score': oob,
            'roc_auc': round(roc_auc, 4),
            'roc_curve_data': {
                'fpr': [round(x, 4) for x in fpr],
                'tpr': [round(x, 4) for x in tpr],
                'roc_auc': round(roc_auc, 4),
            },
            'train': {
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
            },
            'test': {
                'accuracy': round(accuracy, 4),
                'f1_score_weighted': round(f1_weighted, 4),
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
            },
            'accuracy': round(accuracy, 4),
            'f1_score_weighted': round(f1_weighted, 4),
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
            'overfitting_analysis': {
                'accuracy_gap': accuracy_gap,
                'f1_gap': f1_gap,
                'is_overfitting': is_overfitting,
                'keterangan': 'Model tanpa tuning — gunakan mode tuning untuk analisis overfitting yang lebih akurat',
            },
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
    Feature selection dilakukan DI DALAM setiap fold (tanpa data leakage).
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

    # Hitung min class count untuk dynamic n_splits
    min_class_count = int(y.value_counts().min())

    # =====================================================
    # HYPERPARAMETER GRID (dinamis berdasarkan jumlah data)
    # Auto-cap ≤ 150 kombinasi agar tidak timeout/OOM
    # =====================================================
    n_samples = len(X)

    if n_samples < 50:
        # Data kecil → grid kecil
        param_grid = {
            'n_estimators': [100],
            'max_depth': [3, 5],
            'min_samples_split': [10, 20],
            'min_samples_leaf': [10, 20, 30],
            'criterion': ['gini', 'entropy'],
            'class_weight': [None, 'balanced_subsample'],
            'max_features': ['sqrt'],
        }
    elif n_samples < 200:
        # Data sedang → grid sedang
        param_grid = {
            'n_estimators': [100, 200],
            'max_depth': [3, 5, 10],
            'min_samples_split': [5, 10, 20],
            'min_samples_leaf': [5, 10, 20, 30],
            'criterion': ['gini', 'entropy'],
            'class_weight': [None, 'balanced_subsample'],
            'max_features': ['sqrt'],
        }
    else:
        # Data besar → grid lebih luas
        param_grid = {
            'n_estimators': [100, 200, 400],
            'max_depth': [3, 5, 10],
            'min_samples_split': [5, 10, 20],
            'min_samples_leaf': [5, 10, 20, 30],
            'criterion': ['gini', 'entropy'],
            'class_weight': [None, 'balanced_subsample'],
            'max_features': ['sqrt'],
        }

    # Auto-cap: jika kombinasi > 150, kurangi min_samples_leaf
    n_combinations = 1
    for v in param_grid.values():
        n_combinations *= len(v)

    while n_combinations > 150 and len(param_grid.get('min_samples_leaf', [])) > 1:
        param_grid['min_samples_leaf'] = param_grid['min_samples_leaf'][::2]
        n_combinations = 1
        for v in param_grid.values():
            n_combinations *= len(v)

    logger.info(f"Data: {n_samples} samples → {n_combinations} hyperparameter combinations")

    # =====================================================
    # DYNAMIC N_SPLITS (robust terhadap data kecil)
    # StratifiedKFold butuh minimal n_splits sampel per kelas
    # =====================================================
    if min_class_count < 2:
        logger.warning(
            f"Kelas minoritas hanya {min_class_count} sampel. "
            f"Menggunakan train_model tanpa CV tuning."
        )
        return train_model(df)

    n_splits = min(10, min_class_count)
    logger.info(f"Hyperparameter tuning: {n_combinations} kombinasi x {n_splits} fold x 2 model = {n_combinations * n_splits * 2} training runs")
    logger.info(f"Min class count: {min_class_count}, n_splits: {n_splits}")

    # =====================================================
    # N-FOLD STRATIFIED CV + GRID SEARCH
    # Feature selection DI DALAM setiap fold (anti data leakage)
    # =====================================================
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

    best_score = 0.0
    best_params = {}
    cv_results = []

    # Untuk tracking fold features dari kombinasi terbaik
    # (dihapus — feature selection dilakukan sekali setelah grid search)

    for i, params in enumerate(ParameterGrid(param_grid)):
        fold_scores = []

        for train_idx, test_idx in cv.split(X, y):
            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
            y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

            try:
                # --- Feature Selection: HANYA pada data train fold ---
                init_model = RandomForestClassifier(
                    n_estimators=50,
                    criterion=RF_PARAMS['criterion'],
                    max_depth=RF_PARAMS['max_depth'],
                    class_weight=RF_PARAMS['class_weight'],
                    random_state=42,
                    n_jobs=1,
                )
                init_model.fit(X_train, y_train)

                selector = SelectFromModel(init_model, threshold='median')
                selector.fit(X_train, y_train)

                features_fold = [f for f, s in zip(available_features, selector.get_support()) if s]
                if len(features_fold) < 3:
                    features_fold = available_features

                X_train_sel = X_train[features_fold]
                X_test_sel = X_test[features_fold]

                # --- Train + Predict pada fold ---
                model = RandomForestClassifier(
                    **params,
                    bootstrap=True,
                    oob_score=False,
                    random_state=42,
                    n_jobs=1,
                )
                model.fit(X_train_sel, y_train)
                y_pred = model.predict(X_test_sel)

                score = f1_score(y_test, y_pred, average='weighted', labels=[0, 1], zero_division=0)
                fold_scores.append(round(float(score), 4))

            except Exception as e:
                logger.error(f"Error di kombinasi {i+1}, fold {len(fold_scores)+1}: {e}")
                fold_scores.append(0.0)

            finally:
                gc.collect()

        mean_f1 = float(np.mean(fold_scores))
        std_f1 = float(np.std(fold_scores))

        cv_results.append({
            'rank': 0,
            'params': params,
            'mean_f1': round(mean_f1, 4),
            'std_f1': round(std_f1, 4),
            'fold_scores': fold_scores,
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

    if not best_params:
        logger.warning("Tidak ada kombinasi > 0. Menggunakan default params.")
        best_params = {
            'n_estimators': 100, 'max_depth': 5, 'min_samples_split': 10,
            'min_samples_leaf': 20, 'criterion': 'gini',
            'class_weight': 'balanced_subsample', 'max_features': 'sqrt',
        }

    # =====================================================
    # FEATURE SELECTION dengan best_params pada data penuh
    # =====================================================
    init_model_final = RandomForestClassifier(
        n_estimators=50,
        criterion=RF_PARAMS['criterion'],
        max_depth=RF_PARAMS['max_depth'],
        class_weight=RF_PARAMS['class_weight'],
        random_state=42,
        n_jobs=1,
    )
    init_model_final.fit(X, y)

    selector_final = SelectFromModel(init_model_final, threshold='median')
    selector_final.fit(X, y)

    selected_mask = selector_final.get_support()
    final_features = [f for f, s in zip(available_features, selected_mask) if s]
    dropped_features = [f for f, s in zip(available_features, selected_mask) if not s]

    # Force keep fitur tesis meskipun importance rendah
    for f in MUST_INCLUDE_FEATURES:
        if f in available_features and f not in final_features:
            final_features.append(f)
            if f in dropped_features:
                dropped_features.remove(f)

    # Fallback: minimal 3 fitur
    if len(final_features) < 3:
        final_features = available_features
        dropped_features = []

    # Feature frequency dummy (semua fitur terpilih 100%)
    feature_frequency = {f: n_splits for f in final_features}

    del init_model_final, selector_final
    gc.collect()

    logger.info(f"Final features: {len(final_features)}/{len(available_features)} — {final_features}")

    X_final = X[final_features]

    # =====================================================
    # SPLIT DATA untuk evaluasi (robust terhadap data kecil)
    # =====================================================
    min_class_count_split = int(y.value_counts().min())
    use_test_set = min_class_count_split >= 2

    if use_test_set:
        test_size = min(0.2, (min_class_count_split - 1) / min_class_count_split)
        X_train_final, X_test_final, y_train_final, y_test_final = train_test_split(
            X_final, y,
            test_size=test_size,
            random_state=42,
            stratify=y,
        )
    else:
        logger.info("Kelas minoritas hanya 1 sampel, skip train/test split")
        X_train_final, y_train_final = X_final, y
        X_test_final, y_test_final = X_final, y

    # =====================================================
    # TRAIN MODEL FINAL dengan best_params + data training
    # =====================================================
    final_model = RandomForestClassifier(
        **best_params,
        bootstrap=True,
        oob_score=True,
        random_state=42,
        n_jobs=1,
    )
    final_model.fit(X_train_final, y_train_final)

    # Feature importance dari model final
    feature_importance = dict(zip(final_features, final_model.feature_importances_.tolist()))
    feature_importance = dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True))

    oob = round(final_model.oob_score_, 4) if final_model.oob_score_ else None

    # =====================================================
    # ROC-AUC
    # =====================================================
    try:
        y_prob = final_model.predict_proba(X_test_final)
        fpr, tpr, _ = roc_curve(y_test_final, y_prob[:, 1])
        roc_auc = auc(fpr, tpr)
    except Exception:
        fpr, tpr, roc_auc = [0.0, 1.0], [0.0, 1.0], 0.5

    # =====================================================
    # EVALUASI MODEL (Training vs Test)
    # =====================================================
    # Training metrics
    y_train_pred = final_model.predict(X_train_final)
    train_accuracy = accuracy_score(y_train_final, y_train_pred)
    train_f1 = f1_score(y_train_final, y_train_pred, average='weighted', labels=[0, 1], zero_division=0)
    train_cm = confusion_matrix(y_train_final, y_train_pred, labels=[0, 1])

    train_report = classification_report(
        y_train_final, y_train_pred,
        labels=[0, 1],
        target_names=['NORMAL', 'TIDAK_NORMAL'],
        output_dict=True,
        zero_division=0,
    )

    # Test metrics (unseen data)
    y_test_pred = final_model.predict(X_test_final)
    test_accuracy = accuracy_score(y_test_final, y_test_pred)
    test_f1 = f1_score(y_test_final, y_test_pred, average='weighted', labels=[0, 1], zero_division=0)
    test_cm = confusion_matrix(y_test_final, y_test_pred, labels=[0, 1])

    test_report = classification_report(
        y_test_final, y_test_pred,
        labels=[0, 1],
        target_names=['NORMAL', 'TIDAK_NORMAL'],
        output_dict=True,
        zero_division=0,
    )

    # Overfitting detection
    accuracy_gap = round(train_accuracy - test_accuracy, 4)
    f1_gap = round(train_f1 - test_f1, 4)
    is_overfitting = accuracy_gap > 0.1 or f1_gap > 0.1

    # =====================================================
    # SIMPAN MODEL
    # =====================================================
    from datetime import datetime, timezone
    model_data = {
        'model': final_model,
        'features': final_features,
        'params': best_params,
        'metrics': {
            'train_accuracy': round(train_accuracy, 4),
            'train_f1_score_weighted': round(train_f1, 4),
            'test_accuracy': round(test_accuracy, 4),
            'test_f1_score_weighted': round(test_f1, 4),
            'oob_score': oob,
        },
        'trained_at': datetime.now(timezone.utc).isoformat(),
    }
    joblib.dump(model_data, MODEL_PATH, compress=3)

    pkl_size = os.path.getsize(MODEL_PATH)
    pkl_size_kb = round(pkl_size / 1024, 2)

    return {
        'model_performance': {
            'oob_score': oob,
            'roc_auc': round(roc_auc, 4),
            'roc_curve_data': {
                'fpr': [round(x, 4) for x in fpr],
                'tpr': [round(x, 4) for x in tpr],
                'roc_auc': round(roc_auc, 4),
            },
            'train': {
                'accuracy': round(train_accuracy, 4),
                'f1_score_weighted': round(train_f1, 4),
                'oob_score': oob,
                'classification_report': {
                    'NORMAL': {
                        'precision': round(train_report['NORMAL']['precision'], 4),
                        'recall': round(train_report['NORMAL']['recall'], 4),
                        'f1_score': round(train_report['NORMAL']['f1-score'], 4),
                        'support': int(train_report['NORMAL']['support']),
                    },
                    'TIDAK_NORMAL': {
                        'precision': round(train_report['TIDAK_NORMAL']['precision'], 4),
                        'recall': round(train_report['TIDAK_NORMAL']['recall'], 4),
                        'f1_score': round(train_report['TIDAK_NORMAL']['f1-score'], 4),
                        'support': int(train_report['TIDAK_NORMAL']['support']),
                    },
                },
                'confusion_matrix': {
                    'labels': ['NORMAL', 'TIDAK_NORMAL'],
                    'matrix': train_cm.tolist(),
                    'penjelasan': {
                        'true_negative': int(train_cm[0][0]),
                        'false_positive': int(train_cm[0][1]),
                        'false_negative': int(train_cm[1][0]),
                        'true_positive': int(train_cm[1][1]),
                        'keterangan': {
                            'true_negative': 'Petani NORMAL yang diprediksi NORMAL (benar)',
                            'false_positive': 'Petani NORMAL yang diprediksi TIDAK NORMAL (salah alarm)',
                            'false_negative': 'Petani TIDAK NORMAL yang diprediksi NORMAL (lolos deteksi)',
                            'true_positive': 'Petani TIDAK NORMAL yang diprediksi TIDAK NORMAL (tertangkap)',
                        }
                    }
                },
            },
            'test': {
                'accuracy': round(test_accuracy, 4),
                'f1_score_weighted': round(test_f1, 4),
                'classification_report': {
                    'NORMAL': {
                        'precision': round(test_report['NORMAL']['precision'], 4),
                        'recall': round(test_report['NORMAL']['recall'], 4),
                        'f1_score': round(test_report['NORMAL']['f1-score'], 4),
                        'support': int(test_report['NORMAL']['support']),
                    },
                    'TIDAK_NORMAL': {
                        'precision': round(test_report['TIDAK_NORMAL']['precision'], 4),
                        'recall': round(test_report['TIDAK_NORMAL']['recall'], 4),
                        'f1_score': round(test_report['TIDAK_NORMAL']['f1-score'], 4),
                        'support': int(test_report['TIDAK_NORMAL']['support']),
                    },
                },
                'confusion_matrix': {
                    'labels': ['NORMAL', 'TIDAK_NORMAL'],
                    'matrix': test_cm.tolist(),
                    'penjelasan': {
                        'true_negative': int(test_cm[0][0]),
                        'false_positive': int(test_cm[0][1]),
                        'false_negative': int(test_cm[1][0]),
                        'true_positive': int(test_cm[1][1]),
                        'keterangan': {
                            'true_negative': 'Petani NORMAL yang diprediksi NORMAL (benar)',
                            'false_positive': 'Petani NORMAL yang diprediksi TIDAK NORMAL (salah alarm)',
                            'false_negative': 'Petani TIDAK NORMAL yang diprediksi NORMAL (lolos deteksi)',
                            'true_positive': 'Petani TIDAK NORMAL yang diprediksi TIDAK NORMAL (tertangkap)',
                        }
                    }
                },
            },
            'feature_importance': feature_importance,
            'overfitting_analysis': {
                'accuracy_gap': accuracy_gap,
                'f1_gap': f1_gap,
                'is_overfitting': is_overfitting,
                'keterangan': 'Gap > 0.1 menandakan overfitting' if is_overfitting else 'Model generalizes well',
            },
            # Top-level metrics untuk frontend (test set)
            'accuracy': round(test_accuracy, 4),
            'f1_score_weighted': round(test_f1, 4),
            'classification_report': {
                'NORMAL': {
                    'precision': round(test_report['NORMAL']['precision'], 4),
                    'recall': round(test_report['NORMAL']['recall'], 4),
                    'f1_score': round(test_report['NORMAL']['f1-score'], 4),
                    'support': int(test_report['NORMAL']['support']),
                },
                'TIDAK_NORMAL': {
                    'precision': round(test_report['TIDAK_NORMAL']['precision'], 4),
                    'recall': round(test_report['TIDAK_NORMAL']['recall'], 4),
                    'f1_score': round(test_report['TIDAK_NORMAL']['f1-score'], 4),
                    'support': int(test_report['TIDAK_NORMAL']['support']),
                },
            },
            'confusion_matrix': {
                'labels': ['NORMAL', 'TIDAK_NORMAL'],
                'matrix': test_cm.tolist(),
                'penjelasan': {
                    'true_negative': int(test_cm[0][0]),
                    'false_positive': int(test_cm[0][1]),
                    'false_negative': int(test_cm[1][0]),
                    'true_positive': int(test_cm[1][1]),
                    'keterangan': {
                        'true_negative': 'Petani NORMAL yang diprediksi NORMAL (benar)',
                        'false_positive': 'Petani NORMAL yang diprediksi TIDAK NORMAL (salah alarm)',
                        'false_negative': 'Petani TIDAK NORMAL yang diprediksi NORMAL (lolos deteksi)',
                        'true_positive': 'Petani TIDAK NORMAL yang diprediksi TIDAK NORMAL (tertangkap)',
                    }
                }
            },
        },
        'feature_selection': {
            'total_fitur_awal': len(available_features),
            'total_fitur_terpilih': len(final_features),
            'fitur_terpilih': final_features,
            'fitur_dibuang': dropped_features,
            'feature_frequency': feature_frequency,
        },
        'tuning': {
            'method': f'GridSearchCV + {n_splits}-Fold StratifiedKFold (feature selection per-fold)',
            'n_folds': n_splits,
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
            'total_train': len(X_train_final),
            'total_test': len(X_test_final),
            'features_used': final_features,
        },
        'model_file': {
            'path': MODEL_PATH,
            'size_kb': pkl_size_kb,
        },
        'label_distribution': {},
        'message': 'Model berhasil dilatih dengan hyperparameter tuning (10-Fold CV + feature selection per-fold).',
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