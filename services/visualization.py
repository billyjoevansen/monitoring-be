import matplotlib
matplotlib.use('Agg')  # Non-GUI backend (wajib untuk server)

import matplotlib.pyplot as plt
import numpy as np
import io
import base64


def fig_to_base64(fig) -> str:
    """Konversi matplotlib figure ke base64 string untuk dikirim ke frontend."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()
    plt.close(fig)
    return img_base64


def plot_confusion_matrix(cm: list, labels: list) -> str:
    """
    Visualisasi Confusion Matrix.

    ┌─────────────────┬─────────────────┐
    │  True Negative   │  False Positive  │
    │  (Normal→Normal) │  (Normal→TdkNrm) │
    ├─────────────────┼─────────────────┤
    │  False Negative  │  True Positive   │
    │  (TdkNrm→Normal) │ (TdkNrm→TdkNrm) │
    └─────────────────┴─────────────────┘
    """
    fig, ax = plt.subplots(figsize=(8, 6))
    cm_array = np.array(cm)

    # Warna
    cmap = plt.cm.Blues
    im = ax.imshow(cm_array, interpolation='nearest', cmap=cmap)
    ax.figure.colorbar(im, ax=ax, shrink=0.8)

    # Label
    ax.set(
        xticks=np.arange(len(labels)),
        yticks=np.arange(len(labels)),
        xticklabels=labels,
        yticklabels=labels,
        ylabel='Label Aktual',
        xlabel='Label Prediksi',
        title='Confusion Matrix',
    )
    ax.xaxis.set_label_position('bottom')

    # Angka di dalam kotak
    thresh = cm_array.max() / 2.0
    for i in range(len(labels)):
        for j in range(len(labels)):
            ax.text(j, i, format(cm_array[i, j], 'd'),
                    ha='center', va='center', fontsize=18, fontweight='bold',
                    color='white' if cm_array[i, j] > thresh else 'black')

    fig.tight_layout()
    return fig_to_base64(fig)


def plot_feature_importance(feature_importance: dict, top_n: int = 10) -> str:
    """
    Visualisasi Feature Importance (horizontal bar chart).
    Menampilkan top N fitur paling berpengaruh.
    """
    # Ambil top N
    sorted_features = dict(list(feature_importance.items())[:top_n])
    features = list(sorted_features.keys())
    importances = list(sorted_features.values())

    # Balik urutan agar yang tertinggi di atas
    features = features[::-1]
    importances = importances[::-1]

    fig, ax = plt.subplots(figsize=(10, 6))

    colors = plt.cm.viridis(np.linspace(0.3, 0.9, len(features)))
    bars = ax.barh(features, importances, color=colors)

    # Tambah nilai di ujung bar
    for bar, imp in zip(bars, importances):
        ax.text(bar.get_width() + 0.002, bar.get_y() + bar.get_height() / 2,
                f'{imp:.4f}', ha='left', va='center', fontsize=10)

    ax.set_xlabel('Importance Score')
    ax.set_title(f'Top {top_n} Feature Importance')
    ax.set_xlim(0, max(importances) * 1.2)

    fig.tight_layout()
    return fig_to_base64(fig)


def plot_classification_report(report: dict) -> str:
    """
    Visualisasi Classification Report (grouped bar chart).
    Menampilkan Precision, Recall, F1-Score per kelas.
    """
    classes = list(report.keys())
    metrics = ['precision', 'recall', 'f1_score']
    metric_labels = ['Precision', 'Recall', 'F1-Score']

    x = np.arange(len(classes))
    width = 0.25

    fig, ax = plt.subplots(figsize=(10, 6))

    colors = ['#2196F3', '#FF9800', '#4CAF50']

    for i, (metric, label, color) in enumerate(zip(metrics, metric_labels, colors)):
        values = [report[cls][metric] for cls in classes]
        bars = ax.bar(x + i * width, values, width, label=label, color=color)

        # Nilai di atas bar
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                    f'{val:.2f}', ha='center', va='bottom', fontsize=10, fontweight='bold')

    ax.set_xlabel('Kelas')
    ax.set_ylabel('Score')
    ax.set_title('Classification Report')
    ax.set_xticks(x + width)
    ax.set_xticklabels(classes)
    ax.set_ylim(0, 1.15)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    fig.tight_layout()
    return fig_to_base64(fig)


def plot_label_distribution(distribution: dict) -> str:
    """
    Visualisasi distribusi label (pie chart + bar chart).
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    labels = ['NORMAL', 'TIDAK NORMAL']
    sizes = [distribution['normal'], distribution['tidak_normal']]
    colors_pie = ['#4CAF50', '#F44336']
    explode = (0.05, 0.05)

    # Pie Chart
    wedges, texts, autotexts = ax1.pie(
        sizes, explode=explode, labels=labels, colors=colors_pie,
        autopct='%1.1f%%', shadow=True, startangle=90,
        textprops={'fontsize': 12},
    )
    for autotext in autotexts:
        autotext.set_fontweight('bold')
    ax1.set_title('Distribusi Label', fontsize=14, fontweight='bold')

    # Bar Chart
    bars = ax2.bar(labels, sizes, color=colors_pie, edgecolor='white', linewidth=2)
    for bar, size in zip(bars, sizes):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2,
                 str(size), ha='center', va='bottom', fontsize=14, fontweight='bold')

    ax2.set_ylabel('Jumlah Petani')
    ax2.set_title(f'Total: {distribution["total_petani"]} Petani', fontsize=14, fontweight='bold')
    ax2.grid(axis='y', alpha=0.3)

    fig.tight_layout()
    return fig_to_base64(fig)


def plot_reconciliation_summary(summary: dict) -> str:
    """
    Visualisasi ringkasan rekonsiliasi (status penebusan + perbandingan pupuk).
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

    # --- 1. Status Penebusan (Horizontal Bar) ---
    status = summary['status_penebusan']
    status_labels = [
        'Tebus Lengkap',
        'Tebus Sebagian',
        'Tebus Melebihi',
        'Belum Menebus',
    ]
    status_values = [
        status['tebus_lengkap'],
        status['tebus_sebagian'],
        status['tebus_melebihi'],
        status['belum_menebus'],
    ]
    status_colors = ['#4CAF50', '#FF9800', '#F44336', '#9E9E9E']

    bars = ax1.barh(status_labels, status_values, color=status_colors)
    for bar, val in zip(bars, status_values):
        ax1.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                 str(val), ha='left', va='center', fontsize=12, fontweight='bold')

    ax1.set_xlabel('Jumlah Petani')
    ax1.set_title('Status Penebusan', fontsize=14, fontweight='bold')
    ax1.invert_yaxis()

    # --- 2. Perbandingan Pupuk (Grouped Bar) ---
    pupuk_data = summary.get('pupuk', {})
    if pupuk_data:
        pupuk_names = [p.upper() for p in pupuk_data.keys()]
        diajukan = [pupuk_data[p]['total_diajukan_kg'] for p in pupuk_data]
        ditebus = [pupuk_data[p]['total_ditebus_kg'] for p in pupuk_data]

        x = np.arange(len(pupuk_names))
        width = 0.35

        bars1 = ax2.bar(x - width / 2, diajukan, width, label='Diajukan', color='#2196F3')
        bars2 = ax2.bar(x + width / 2, ditebus, width, label='Ditebus', color='#FF9800')

        ax2.set_xlabel('Jenis Pupuk')
        ax2.set_ylabel('Jumlah (Kg)')
        ax2.set_title('Perbandingan Pupuk Diajukan vs Ditebus', fontsize=14, fontweight='bold')
        ax2.set_xticks(x)
        ax2.set_xticklabels(pupuk_names)
        ax2.legend()
        ax2.grid(axis='y', alpha=0.3)

    fig.tight_layout()
    return fig_to_base64(fig)


def plot_kios_compliance(summary: dict) -> str:
    """
    Visualisasi kesesuaian kios (donut chart).
    """
    fig, ax = plt.subplots(figsize=(8, 6))

    kios = summary['kios']
    sizes = [kios['sesuai'], kios['tidak_sesuai']]
    labels = ['Kios Sesuai', 'Kios Tidak Sesuai']
    colors = ['#4CAF50', '#F44336']

    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=colors,
        autopct='%1.1f%%', startangle=90,
        pctdistance=0.75, textprops={'fontsize': 12},
    )

    for autotext in autotexts:
        autotext.set_fontweight('bold')

    # Donut hole
    centre_circle = plt.Circle((0, 0), 0.50, fc='white')
    ax.add_artist(centre_circle)

    ax.text(0, 0, f'{kios["sesuai"]}/{kios["sesuai"] + kios["tidak_sesuai"]}',
            ha='center', va='center', fontsize=20, fontweight='bold')

    ax.set_title('Kesesuaian Kios Penebusan', fontsize=14, fontweight='bold')

    fig.tight_layout()
    return fig_to_base64(fig)