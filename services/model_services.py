import os
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, classification_report


class ModelService:
    MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'models')
    MODEL_PATH = os.path.join(MODEL_DIR, 'random_forest.joblib')
    CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'model_config.json')

    FEATURE_COLUMNS = [
        'total_pupuk_diajukan_kg',
        'total_pupuk_ditebus_kg',
        'selisih_total_kg',
        'kios_sesuai',
    ]

    def __init__(self):
        os.makedirs(self.MODEL_DIR, exist_ok=True)

    def _load_config(self):
        """Load hyperparameters dari config file."""
        try:
            with open(self.CONFIG_PATH, 'r') as f:
                config = json.load(f)
            return config
        except FileNotFoundError:
            return self._default_config()

    def _default_config(self):
        return {
            'hyperparameters': {
                'n_estimators': 100,
                'criterion': 'gini',
                'max_depth': None,
                'max_features': 'sqrt',
                'min_samples_split': 2,
                'min_samples_leaf': 1,
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
            },
        }

    def _prepare_features(self, detail):
        """
        Konversi data rekonsiliasi ke feature matrix.
        """
        df = pd.DataFrame(detail)

        # Pastikan kolom numerik
        for col in ['total_pupuk_diajukan_kg', 'total_pupuk_ditebus_kg', 'selisih_total_kg']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Konversi kios_sesuai ke numerik (True/False → 1/0)
        if 'kios_sesuai' in df.columns:
            df['kios_sesuai'] = df['kios_sesuai'].apply(
                lambda x: 1 if x in [True, 'true', 'True', 'Ya', 'ya', 1, '1'] else 0
            )

        # Pastikan semua feature column ada
        for col in self.FEATURE_COLUMNS:
            if col not in df.columns:
                df[col] = 0

        return df

    def classify(self, detail):
        """
        Klasifikasi data menggunakan model yang sudah dilatih.
        """
        if not os.path.exists(self.MODEL_PATH):
            raise FileNotFoundError('Model belum dilatih.')

        model = joblib.load(self.MODEL_PATH)
        df = self._prepare_features(detail)
        X = df[self.FEATURE_COLUMNS].values

        predictions = model.predict(X)
        probabilities = model.predict_proba(X)

        # Ambil confidence (probabilitas kelas yang diprediksi)
        confidence = np.max(probabilities, axis=1)

        # Bangun hasil detail
        result_detail = []
        for i, row in df.iterrows():
            original = detail[i] if i < len(detail) else {}
            result_detail.append({
                'nama_petani': original.get('nama_petani', '-'),
                'nik': original.get('nik', '-'),
                'poktan': original.get('poktan', '-'),
                'kios_sesuai': bool(row.get('kios_sesuai', False)),
                'total_pupuk_diajukan': float(row.get('total_pupuk_diajukan_kg', 0)),
                'total_pupuk_ditebus': float(row.get('total_pupuk_ditebus_kg', 0)),
                'selisih_total_pupuk': float(row.get('selisih_total_kg', 0)),
                'status': str(predictions[i]),
                'confidence': round(float(confidence[i]), 4),
            })

        normal_count = int(np.sum(predictions == 'NORMAL'))
        tidak_normal_count = int(np.sum(predictions == 'TIDAK NORMAL'))
        total = len(predictions)

        return {
            'summary': {
                'total_petani': total,
                'normal': normal_count,
                'tidak_normal': tidak_normal_count,
                'persentase_normal': round(normal_count / total * 100, 1) if total > 0 else 0,
                'persentase_tidak_normal': round(tidak_normal_count / total * 100, 1) if total > 0 else 0,
            },
            'detail': result_detail,
        }

    def train_with_dummy(self):
        """
        Training model dengan data dummy.
        """
        config = self._load_config()
        hp = config['hyperparameters']
        tc = config['training_config']

        # Generate data dummy
        np.random.seed(tc['random_state'])
        n_samples = 200

        data = {
            'total_pupuk_diajukan_kg': np.random.uniform(50, 500, n_samples),
            'total_pupuk_ditebus_kg': np.random.uniform(0, 500, n_samples),
            'selisih_total_kg': np.random.uniform(-100, 200, n_samples),
            'kios_sesuai': np.random.choice([0, 1], n_samples, p=[0.3, 0.7]),
        }

        df = pd.DataFrame(data)

        # Label: NORMAL jika selisih kecil dan kios sesuai
        labels = []
        for _, row in df.iterrows():
            selisih_ratio = abs(row['selisih_total_kg']) / max(row['total_pupuk_diajukan_kg'], 1)
            if selisih_ratio < 0.2 and row['kios_sesuai'] == 1:
                labels.append('NORMAL')
            elif selisih_ratio < 0.4 and row['kios_sesuai'] == 1:
                labels.append('NORMAL' if np.random.random() > 0.3 else 'TIDAK NORMAL')
            else:
                labels.append('TIDAK NORMAL')

        y = np.array(labels)
        X = df[self.FEATURE_COLUMNS].values

        # Split
        stratify_param = y if tc['stratify'] else None
        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=tc['test_size'],
            random_state=tc['random_state'],
            stratify=stratify_param,
        )

        # Build model
        model_params = {
            'n_estimators': hp['n_estimators'],
            'criterion': hp['criterion'],
            'max_depth': hp['max_depth'],
            'max_features': hp['max_features'],
            'min_samples_split': hp['min_samples_split'],
            'min_samples_leaf': hp['min_samples_leaf'],
            'class_weight': hp['class_weight'],
            'bootstrap': hp['bootstrap'],
            'oob_score': hp['oob_score'] if hp['bootstrap'] else False,
            'random_state': hp['random_state'],
            'n_jobs': hp['n_jobs'],
        }

        model = RandomForestClassifier(**model_params)
        model.fit(X_train, y_train)

        # Evaluate
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average='weighted')
        report = classification_report(y_test, y_pred, output_dict=True)

        # Save model
        joblib.dump(model, self.MODEL_PATH)
        model_size = os.path.getsize(self.MODEL_PATH) / 1024

        result = {
            'model_performance': {
                'accuracy': round(accuracy, 4),
                'f1_score_weighted': round(f1, 4),
                'classification_report': report,
            },
            'model_file': {
                'path': self.MODEL_PATH,
                'size_kb': round(model_size, 1),
            },
            'training_data': {
                'total_samples': n_samples,
                'train_samples': len(X_train),
                'test_samples': len(X_test),
            },
            'feature_importance': {
                col: round(float(imp), 4)
                for col, imp in zip(self.FEATURE_COLUMNS, model.feature_importances_)
            },
        }

        if hp['oob_score'] and hp['bootstrap']:
            result['model_performance']['oob_score'] = round(model.oob_score_, 4)

        return result

    def get_model_info(self):
        """
        Cek apakah model sudah ada dan info-nya.
        """
        if not os.path.exists(self.MODEL_PATH):
            raise FileNotFoundError('Model belum dilatih.')

        model = joblib.load(self.MODEL_PATH)
        model_size = os.path.getsize(self.MODEL_PATH) / 1024

        return {
            'trained': True,
            'n_estimators': model.n_estimators,
            'n_features': model.n_features_in_,
            'classes': model.classes_.tolist(),
            'size_kb': round(model_size, 1),
        }