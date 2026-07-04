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


# =====================================================
# K-FOLD CV VISUALIZATION
# =====================================================

def plot_cv_fold_scores(cv_results: list, best_params: dict) -> str:
    """
    Bar chart: F1 score per fold untuk kombinasi terbaik.
    Garis horizontal = rata-rata, shading = std dev.
    """
    best = cv_results[0]
    fold_scores = best['fold_scores']
    mean_f1 = best['mean_f1']
    std_f1 = best['std_f1']

    fig, ax = plt.subplots(figsize=(10, 6))

    folds = list(range(1, len(fold_scores) + 1))
    colors = ['#4CAF50' if s >= mean_f1 else '#FF9800' for s in fold_scores]

    bars = ax.bar(folds, fold_scores, color=colors, edgecolor='white', linewidth=1.5)

    ax.axhline(y=mean_f1, color='#2196F3', linestyle='--', linewidth=2,
               label=f'Mean: {mean_f1:.4f}')

    ax.axhspan(mean_f1 - std_f1, mean_f1 + std_f1, alpha=0.15, color='#2196F3',
               label=f'Std: \u00b1{std_f1:.4f}')

    for bar, score in zip(bars, fold_scores):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.002,
                f'{score:.4f}', ha='center', va='bottom', fontsize=10, fontweight='bold')

    params_str = ', '.join(f'{k}={v}' for k, v in best_params.items())
    ax.set_xlabel('Fold')
    ax.set_ylabel('F1 Score (Weighted)')
    ax.set_title(f'K-Fold Cross Validation \u2014 Per Fold Performance\n{params_str}')
    ax.set_xticks(folds)
    ax.set_ylim(min(fold_scores) - 0.05, max(fold_scores) + 0.05)
    ax.legend(loc='lower right')
    ax.grid(axis='y', alpha=0.3)

    fig.tight_layout()
    return fig_to_base64(fig)


def plot_cv_comparison(cv_results: list, top_n: int = 10) -> str:
    """
    Horizontal bar chart: Top N kombinasi terbaik dengan mean F1 +/- std.
    """
    top = cv_results[:top_n]

    labels = []
    for item in top:
        p = item['params']
        parts = []
        if 'n_estimators' in p:
            parts.append(f"n={p['n_estimators']}")
        if 'max_depth' in p:
            parts.append(f"d={p['max_depth'] if p['max_depth'] is not None else 'None'}")
        if 'min_samples_leaf' in p:
            parts.append(f"l={p['min_samples_leaf']}")
        if 'min_samples_split' in p:
            parts.append(f"s={p['min_samples_split']}")
        labels.append(', '.join(parts))

    means = [item['mean_f1'] for item in top]
    stds = [item['std_f1'] for item in top]

    labels = labels[::-1]
    means = means[::-1]
    stds = stds[::-1]

    fig, ax = plt.subplots(figsize=(10, 6))

    colors = ['#2196F3' if i == len(labels) - 1 else '#90CAF9' for i in range(len(labels))]
    bars = ax.barh(labels, means, xerr=stds, color=colors, edgecolor='white',
                   linewidth=1.5, capsize=3)

    for bar, mean, std in zip(bars, means, stds):
        ax.text(bar.get_width() + std + 0.003, bar.get_y() + bar.get_height() / 2,
                f'{mean:.4f} \u00b1{std:.4f}', ha='left', va='center', fontsize=9)

    ax.set_xlabel('Mean F1 Score (Weighted)')
    ax.set_title(f'Top {top_n} Hyperparameter Combinations (by CV F1)')
    ax.set_xlim(0, max(means) + max(stds) + 0.1)
    ax.grid(axis='x', alpha=0.3)

    fig.tight_layout()
    return fig_to_base64(fig)


def plot_cv_boxplot(cv_results: list, top_n: int = 10) -> str:
    """
    Box plot: Distribusi fold scores untuk top N kombinasi.
    """
    top = cv_results[:top_n]

    labels = []
    all_scores = []
    for item in top:
        p = item['params']
        parts = []
        if 'n_estimators' in p:
            parts.append(f"n={p['n_estimators']}")
        if 'max_depth' in p:
            parts.append(f"d={p['max_depth'] if p['max_depth'] is not None else 'None'}")
        if 'min_samples_leaf' in p:
            parts.append(f"l={p['min_samples_leaf']}")
        if 'min_samples_split' in p:
            parts.append(f"s={p['min_samples_split']}")
        labels.append('#' + str(item['rank']) + ' ' + ', '.join(parts))
        all_scores.append(item['fold_scores'])

    fig, ax = plt.subplots(figsize=(12, 6))

    bp = ax.boxplot(all_scores, labels=labels, patch_artist=True, notch=False,
                    medianprops={'color': '#F44336', 'linewidth': 2},
                    whiskerprops={'linewidth': 1.5},
                    capprops={'linewidth': 1.5})

    colors = plt.cm.Purples(np.linspace(0.3, 0.8, len(labels)))
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)

    means = [np.mean(scores) for scores in all_scores]
    ax.scatter(range(1, len(labels) + 1), means, color='#FF9800', zorder=5,
               s=50, marker='D', label='Mean')

    ax.set_ylabel('F1 Score (Weighted)')
    ax.set_title(f'Fold Score Distribution \u2014 Top {top_n} Combinations')
    ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
    ax.legend(loc='lower right')
    ax.grid(axis='y', alpha=0.3)

    fig.tight_layout()
    return fig_to_base64(fig)


def plot_feature_frequency(feature_frequency: dict, n_folds: int = 10, threshold: float = 0.7) -> str:
    """Horizontal bar chart frekuensi fitur muncul di tiap fold CV."""
    if not feature_frequency:
        return ''

    sorted_items = sorted(feature_frequency.items(), key=lambda x: x[1])
    features = [item[0] for item in sorted_items]
    counts = [item[1] for item in sorted_items]

    min_count = int(threshold * n_folds)

    colors = ['#4CAF50' if c >= min_count else '#BDBDBD' for c in counts]

    fig, ax = plt.subplots(figsize=(10, max(4, len(features) * 0.45)))
    bars = ax.barh(features, counts, color=colors, edgecolor='white', linewidth=0.5)

    ax.axvline(x=min_count, color='#F44336', linestyle='--', linewidth=2,
               label=f'Threshold ({min_count}/{n_folds} folds)')

    for bar, count in zip(bars, counts):
        label = f'{count}/{n_folds}'
        x_pos = bar.get_width() + 0.15
        ax.text(x_pos, bar.get_y() + bar.get_height() / 2,
                label, va='center', fontsize=9, fontweight='bold')

    ax.set_xlabel('Jumlah Fold (dari 10)')
    ax.set_title('Feature Frequency — Seberapa Sering Fitur Terpilih per Fold')
    ax.set_xlim(0, n_folds + 1)
    ax.set_xticks(range(0, n_folds + 1))
    ax.legend(loc='lower right')
    ax.grid(axis='x', alpha=0.3)

    fig.tight_layout()
    return fig_to_base64(fig)