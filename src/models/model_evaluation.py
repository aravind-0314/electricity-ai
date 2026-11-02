"""
Model Evaluation and Performance Metrics Utility.

Calculates genuine evaluation metrics on held-out test data.
Never fabricates metrics.
"""

from typing import Dict, Any, List
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix
)

def evaluate_classifier(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: np.ndarray = None
) -> Dict[str, Any]:
    """
    Compute comprehensive classification metrics.
    Handles zero division safely by setting zero_division=0.
    """
    acc = float(accuracy_score(y_true, y_pred))
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))

    roc_auc = None
    if y_proba is not None and len(np.unique(y_true)) > 1:
        try:
            # If 2D probability array passed
            if y_proba.ndim > 1:
                proba_pos = y_proba[:, 1]
            else:
                proba_pos = y_proba
            roc_auc = float(roc_auc_score(y_true, proba_pos))
        except Exception:
            roc_auc = None

    cm = confusion_matrix(y_true, y_pred).tolist()

    return {
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
        "roc_auc": round(roc_auc, 4) if roc_auc is not None else None,
        "confusion_matrix": cm,
        "true_negatives": cm[0][0] if len(cm) > 1 else cm[0][0],
        "false_positives": cm[0][1] if len(cm) > 1 else 0,
        "false_negatives": cm[1][0] if len(cm) > 1 else 0,
        "true_positives": cm[1][1] if len(cm) > 1 else 0,
        "evaluation_notes": "Evaluated against held-out synthetic test set. Synthetic benchmark performance does not guarantee real-world electricity theft detection accuracy."
    }

