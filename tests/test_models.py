import pytest
import numpy as np
from src.features.feature_engineering import FeatureExtractor, FEATURE_NAMES
from src.models.isolation_forest import IsolationForestPipeline
from src.models.random_forest import RandomForestBenchmark
from src.models.model_evaluation import evaluate_classifier

def test_isolation_forest_pipeline():
    """Verify Isolation Forest fitting and score normalization [0.0, 1.0]."""
    fe = FeatureExtractor()
    df = fe.extract_all_features()
    X, ids, df_feat = fe.get_feature_matrix(df)

    pipeline = IsolationForestPipeline(n_estimators=50, contamination=0.1)
    df_preds = pipeline.fit_predict(X, df_feat)

    assert len(df_preds) == 500
    assert "anomaly_score" in df_preds.columns
    assert "review_priority" in df_preds.columns
    assert "diagnostic_reason" in df_preds.columns

    # Verify normalization bounds
    scores = df_preds["anomaly_score"].values
    assert (scores >= 0.0).all() and (scores <= 1.0).all()

    # Verify priority rule consistency
    for _, row in df_preds.iterrows():
        score = row["anomaly_score"]
        p = row["review_priority"]
        if score >= 0.75:
            assert p == "Critical"
        elif score >= 0.60:
            assert p == "High"
        elif score >= 0.45:
            assert p == "Medium"
        else:
            assert p == "Low"

def test_random_forest_benchmark():
    """Verify Random Forest benchmark evaluation on held-out test data."""
    fe = FeatureExtractor()
    df = fe.extract_all_features()
    rf = RandomForestBenchmark(n_estimators=50)
    metrics = rf.train_and_evaluate(df)

    assert "accuracy" in metrics
    assert "precision" in metrics
    assert "recall" in metrics
    assert "f1_score" in metrics
    assert "roc_auc" in metrics
    assert "confusion_matrix" in metrics

    # Non-trivial metrics
    assert metrics["accuracy"] > 0.70
    assert metrics["test_samples"] == 150
    assert len(metrics["confusion_matrix"]) == 2

def test_evaluation_utility():
    """Verify evaluation metric calculations."""
    y_true = np.array([0, 0, 1, 1])
    y_pred = np.array([0, 0, 1, 1])
    res = evaluate_classifier(y_true, y_pred)
    assert res["accuracy"] == 1.0
    assert res["precision"] == 1.0
    assert res["recall"] == 1.0
    assert res["f1_score"] == 1.0

