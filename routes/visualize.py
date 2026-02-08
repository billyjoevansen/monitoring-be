from flask import Blueprint, request, jsonify
from services.visualization import (
    plot_confusion_matrix,
    plot_feature_importance,
    plot_classification_report,
    plot_label_distribution,
    plot_reconciliation_summary,
    plot_kios_compliance,
)

visualize_bp = Blueprint('visualize', __name__)


@visualize_bp.route('/api/visualize/training', methods=['POST'])
def visualize_training():
    """
    Generate visualisasi dari hasil training.

    Body JSON: hasil dari /api/train (model_performance + label_distribution)
    Returns: base64 encoded images
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Body JSON tidak boleh kosong.'}), 400

        perf = data.get('model_performance', {})
        dist = data.get('label_distribution', {})

        charts = {}

        # 1. Confusion Matrix
        cm_data = perf.get('confusion_matrix', {})
        if cm_data:
            charts['confusion_matrix'] = plot_confusion_matrix(
                cm=cm_data['matrix'],
                labels=cm_data['labels'],
            )

        # 2. Feature Importance
        fi_data = perf.get('feature_importance', {})
        if fi_data:
            charts['feature_importance'] = plot_feature_importance(fi_data)

        # 3. Classification Report
        cr_data = perf.get('classification_report', {})
        if cr_data:
            charts['classification_report'] = plot_classification_report(cr_data)

        # 4. Label Distribution
        if dist:
            charts['label_distribution'] = plot_label_distribution(dist)

        return jsonify({
            'charts': charts,
            'total_charts': len(charts),
            'message': 'Visualisasi berhasil di-generate.',
        }), 200

    except Exception as e:
        return jsonify({'error': f'Gagal generate visualisasi: {str(e)}'}), 500


@visualize_bp.route('/api/visualize/reconciliation', methods=['POST'])
def visualize_reconciliation():
    """
    Generate visualisasi dari hasil rekonsiliasi.

    Body JSON: hasil dari /api/reconcile (summary)
    Returns: base64 encoded images
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Body JSON tidak boleh kosong.'}), 400

        summary = data.get('summary', {})

        charts = {}

        # 1. Status Penebusan + Perbandingan Pupuk
        if summary:
            charts['reconciliation_summary'] = plot_reconciliation_summary(summary)

        # 2. Kesesuaian Kios
        if 'kios' in summary:
            charts['kios_compliance'] = plot_kios_compliance(summary)

        return jsonify({
            'charts': charts,
            'total_charts': len(charts),
            'message': 'Visualisasi rekonsiliasi berhasil di-generate.',
        }), 200

    except Exception as e:
        return jsonify({'error': f'Gagal generate visualisasi: {str(e)}'}), 500