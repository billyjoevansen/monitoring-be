import requests
import base64
import os

BASE_URL = 'http://localhost:5000'

# =====================================================
# 1. TEST HEALTH CHECK
# =====================================================
print("=" * 60)
print("🔍 Testing Health Check...")
r = requests.get(f'{BASE_URL}/api/health')
print(f"Status: {r.status_code}")
print(f"Response: {r.json()}")

# =====================================================
# 2. TEST REKONSILIASI (Output 1)
# =====================================================
print("\n" + "=" * 60)
print("📋 Testing Rekonsiliasi (Output 1)...")
files = {
    'rdkk': open('dummy_data/data_rdkk.xlsx', 'rb'),
    'siverval': open('dummy_data/data_siverval.xlsx', 'rb'),
}
r = requests.post(f'{BASE_URL}/api/reconcile', files=files)
reconcile_result = r.json()

print(f"Status: {r.status_code}")

if r.status_code == 200:
    summary = reconcile_result['summary']
    print(f"\n📊 Ringkasan Rekonsiliasi:")
    print(f"   Total Petani: {summary['total_petani']}")

    print(f"\n   📦 Status Penebusan:")
    status = summary['status_penebusan']
    print(f"      Tebus Lengkap     : {status['tebus_lengkap']}")
    print(f"      Tebus Sebagian    : {status['tebus_sebagian']}")
    print(f"      Tebus Melebihi    : {status['tebus_melebihi']}")
    print(f"      Belum Menebus     : {status['belum_menebus']}")

    print(f"\n   🏪 Kesesuaian Kios:")
    kios = summary['kios']
    print(f"      Sesuai        : {kios['sesuai']} ({kios['persentase_sesuai']}%)")
    print(f"      Tidak Sesuai  : {kios['tidak_sesuai']}")

    print(f"\n   🧪 Rekonsiliasi Per Jenis Pupuk:")
    for pupuk, data in summary['pupuk'].items():
        print(f"      {pupuk.upper():15} | Ajukan: {data['total_diajukan_kg']:>10.0f} kg | "
              f"Tebus: {data['total_ditebus_kg']:>10.0f} kg | "
              f"Selisih: {data['selisih_kg']:>10.0f} kg | "
              f"Tebus: {data['persentase_tebus']}%")
else:
    print(f"Error: {reconcile_result}")

for f in files.values():
    f.close()

# =====================================================
# 3. TEST TRAINING
# =====================================================
print("\n" + "=" * 60)
print("🤖 Training Model (Output 2 - Step 1)...")
files = {
    'rdkk': open('dummy_data/data_rdkk.xlsx', 'rb'),
    'siverval': open('dummy_data/data_siverval.xlsx', 'rb'),
}
r = requests.post(f'{BASE_URL}/api/train', files=files)
train_result = r.json()

print(f"Status: {r.status_code}")

if r.status_code == 200:
    perf = train_result['model_performance']
    print(f"\n📊 Hasil Evaluasi Model:")
    print(f"   Accuracy : {perf['accuracy']}")
    print(f"   F1 Score : {perf['f1_score_weighted']}")

    print(f"\n📋 Classification Report:")
    for kelas, metrics in perf['classification_report'].items():
        print(f"   {kelas}:")
        print(f"     Precision : {metrics['precision']}")
        print(f"     Recall    : {metrics['recall']}")
        print(f"     F1 Score  : {metrics['f1_score']}")
        print(f"     Support   : {metrics['support']}")

    print(f"\n🔢 Confusion Matrix:")
    cm = perf['confusion_matrix']
    print(f"   Labels: {cm['labels']}")
    for row in cm['matrix']:
        print(f"   {row}")

    # Feature Selection
    if 'feature_selection' in train_result:
        fs = train_result['feature_selection']
        print(f"\n🎯 Feature Selection:")
        print(f"   Fitur awal    : {fs['total_fitur_awal']}")
        print(f"   Fitur terpilih: {fs['total_fitur_terpilih']}")
        print(f"   Fitur dibuang : {fs['fitur_dibuang']}")

    print(f"\n🏆 Top 5 Feature Importance:")
    fi = perf['feature_importance']
    for i, (feat, imp) in enumerate(list(fi.items())[:5]):
        print(f"   {i+1}. {feat}: {imp:.4f}")

    print(f"\n📦 Label Distribution:")
    dist = train_result['label_distribution']
    print(f"   Total       : {dist['total_petani']}")
    print(f"   Normal      : {dist['normal']} ({dist['persentase_normal']}%)")
    print(f"   Tidak Normal: {dist['tidak_normal']} ({dist['persentase_tidak_normal']}%)")

    # Model file size
    if 'model_file' in train_result:
        print(f"\n💾 Model File: {train_result['model_file']['size_kb']} KB")
else:
    print(f"Error: {train_result}")

for f in files.values():
    f.close()

# =====================================================
# 4. TEST PREDIKSI (Output 2 - Step 2)
# =====================================================
print("\n" + "=" * 60)
print("🔮 Testing Prediksi (Output 2)...")
files = {
    'rdkk': open('dummy_data/data_rdkk.xlsx', 'rb'),
    'siverval': open('dummy_data/data_siverval.xlsx', 'rb'),
}
r = requests.post(f'{BASE_URL}/api/predict', files=files)
predict_result = r.json()

print(f"Status: {r.status_code}")

if r.status_code == 200:
    summary = predict_result['summary']
    print(f"\n📊 Summary Prediksi:")
    print(f"   Total Petani     : {summary['total_petani']}")
    print(f"   Normal           : {summary['normal']} ({summary['persentase_normal']}%)")
    print(f"   Tidak Normal     : {summary['tidak_normal']} ({summary['persentase_tidak_normal']}%)")

    print(f"\n   👨‍🌾 Sample 5 Petani Pertama (Prediksi):")
    for petani in predict_result['detail'][:5]:
        status_icon = "✅" if petani['status'] == 'NORMAL' else "❌"
        print(f"\n   {status_icon} {petani['nama_petani']} ({petani['nik']})")
        print(f"      Status     : {petani['status']}")
        print(f"      Confidence : {petani['confidence']}")
        print(f"      Kios Sesuai: {petani['kios_sesuai']}")
else:
    print(f"Error: {predict_result}")

for f in files.values():
    f.close()

# =====================================================
# 5. TEST VISUALISASI TRAINING
# =====================================================
print("\n" + "=" * 60)
print("📊 Testing Visualisasi Training...")

if r.status_code == 200 and 'model_performance' in train_result:
    r = requests.post(f'{BASE_URL}/api/visualize/training', json=train_result)
    viz_result = r.json()
    print(f"Status: {r.status_code}")

    if r.status_code == 200:
        charts = viz_result['charts']
        print(f"   Total Charts: {viz_result['total_charts']}")

        # Simpan chart ke file PNG
        os.makedirs('dummy_data/charts', exist_ok=True)
        for name, img_base64 in charts.items():
            img_data = base64.b64decode(img_base64)
            filepath = f'dummy_data/charts/{name}.png'
            with open(filepath, 'wb') as f:
                f.write(img_data)
            print(f"   ✅ Saved: {filepath}")
    else:
        print(f"   Error: {viz_result}")

# =====================================================
# 6. TEST VISUALISASI REKONSILIASI
# =====================================================
print("\n" + "=" * 60)
print("📊 Testing Visualisasi Rekonsiliasi...")

if 'summary' in reconcile_result:
    r = requests.post(f'{BASE_URL}/api/visualize/reconciliation', json=reconcile_result)
    viz_result = r.json()
    print(f"Status: {r.status_code}")

    if r.status_code == 200:
        charts = viz_result['charts']
        print(f"   Total Charts: {viz_result['total_charts']}")

        for name, img_base64 in charts.items():
            img_data = base64.b64decode(img_base64)
            filepath = f'dummy_data/charts/{name}.png'
            with open(filepath, 'wb') as f:
                f.write(img_data)
            print(f"   ✅ Saved: {filepath}")
    else:
        print(f"   Error: {viz_result}")
else:
    print("❌ Rekonsiliasi data tidak tersedia, lewati visualisasi.")

print("\n" + "=" * 60)
print("✅ SEMUA TEST SELESAI!")
print("=" * 60)
print(f"\n🖼️  Buka folder 'dummy_data/charts/' untuk melihat visualisasi!")