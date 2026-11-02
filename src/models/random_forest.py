"""
Random Forest Supervised Benchmark Pipeline.

Trains a Random Forest Classifier on synthetic scenario labels as a benchmark baseline.
Calculates and logs genuine evaluation metrics on held-out test data.
Feature importances and confusion matrix are saved to SQLite and JSON.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import os
import json
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, Optional
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

from config import Config
from database.db import get_db, query_db
from src.features.feature_engineering import FeatureExtractor, FEATURE_NAMES
from src.models.model_evaluation import evaluate_classifier

# Synthetic scenarios representing tampering
TAMPER_SCENARIOS = {"PARTIAL_BYPASS", "METER_FLATLINE", "PEAK_BYPASS"}

class RandomForestBenchmark:
    def __init__(
        self,
        n_estimators: int = Config.RF_N_ESTIMATORS,
        test_size: float = Config.RF_TEST_SIZE,
        random_state: int = Config.RANDOM_SEED
    ):
        self.n_estimators = n_estimators
        self.test_size = test_size
        self.random_state = random_state
        self.model = RandomForestClassifier(
            n_estimators=self.n_estimators,
            random_state=self.random_state,
            class_weight="balanced",
            n_jobs=-1
        )
        self.metrics: Dict[str, Any] = {}
        self.feature_importances: Dict[str, float] = {}

    def prepare_dataset(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Extract features X and synthetic target labels y.
        y = 1 if scenario in TAMPER_SCENARIOS else 0 (NORMAL, TELEMETRY_DROPOUT, VACATION).
        Applies stratified train-test split.
        """
        X = df[FEATURE_NAMES].values.astype(np.float64)
        y = df["simulation_scenario"].apply(lambda s: 1 if s in TAMPER_SCENARIOS else 0).values

        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=self.test_size,
            random_state=self.random_state,
            stratify=y
        )
        return X_train, X_test, y_train, y_test

    def train_and_evaluate(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Train model, evaluate on held-out test set, and store metrics."""
        X_train, X_test, y_train, y_test = self.prepare_dataset(df)

        # Train model
        self.model.fit(X_train, y_train)

        # Evaluate on test set
        y_pred = self.model.predict(X_test)
        y_proba = self.model.predict_proba(X_test)

        self.metrics = evaluate_classifier(y_test, y_pred, y_proba)
        self.metrics["train_samples"] = len(X_train)
        self.metrics["test_samples"] = len(X_test)
        self.metrics["n_estimators"] = self.n_estimators

        # Feature importances
        importances = self.model.feature_importances_
        self.feature_importances = {
            name: round(float(imp), 4)
            for name, imp in sorted(zip(FEATURE_NAMES, importances), key=lambda x: x[1], reverse=True)
        }
        self.metrics["feature_importances"] = self.feature_importances

        return self.metrics

    def predict_all(self, df: pd.DataFrame) -> np.ndarray:
        """Generate predicted tampering probabilities for all consumers."""
        X = df[FEATURE_NAMES].values.astype(np.float64)
        probas = self.model.predict_proba(X)
        return probas[:, 1]  # Probability of class 1

    def save(self, model_path: Optional[Path] = None, metrics_path: Optional[Path] = None):
        """Save model to Joblib and metrics to JSON."""
        m_path = model_path or Config.RF_MODEL_PATH
        met_path = metrics_path or Config.METRICS_PATH
        os.makedirs(os.path.dirname(m_path), exist_ok=True)
        os.makedirs(os.path.dirname(met_path), exist_ok=True)

        joblib.dump({
            "model": self.model,
            "feature_names": FEATURE_NAMES,
            "metrics": self.metrics,
            "feature_importances": self.feature_importances
        }, m_path)

        with open(met_path, "w", encoding="utf-8") as f:
            json.dump(self.metrics, f, indent=2)

def run_random_forest_benchmark(df_features: Optional[pd.DataFrame] = None, verbose: bool = True) -> Dict[str, Any]:
    """Train Random Forest benchmark, evaluate on test set, and save to DB."""
    if df_features is None:
        extractor = FeatureExtractor()
        df_features = extractor.extract_all_features()

    if verbose:
        print("Training Random Forest benchmark on synthetic scenario labels...")

    rf_benchmark = RandomForestBenchmark()
    metrics = rf_benchmark.train_and_evaluate(df_features)
    rf_probas = rf_benchmark.predict_all(df_features)
    rf_benchmark.save()

    # Save metrics to SQLite table model_metrics and update theft_predictions with rf_probability
    with get_db() as conn:
        conn.execute("DELETE FROM model_metrics WHERE model_name = 'Random Forest';")
        conn.execute(
            """INSERT INTO model_metrics (model_name, accuracy, precision, recall, f1_score, roc_auc,
                                          confusion_matrix_json, feature_importance_json, evaluation_notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "Random Forest",
                metrics["accuracy"],
                metrics["precision"],
                metrics["recall"],
                metrics["f1_score"],
                metrics["roc_auc"],
                json.dumps(metrics["confusion_matrix"]),
                json.dumps(metrics["feature_importances"]),
                metrics["evaluation_notes"]
            )
        )

        # Update rf_probability in theft_predictions
        update_data = [
            (float(round(rf_probas[i], 4)), df_features.iloc[i]["consumer_id"])
            for i in range(len(df_features))
        ]
        conn.executemany(
            "UPDATE theft_predictions SET rf_probability = ? WHERE consumer_id = ?",
            update_data
        )

    if verbose:
        print(f"Random Forest Evaluation Metrics (on {metrics['test_samples']} test samples):")
        print(f"  Accuracy:  {metrics['accuracy']*100:.2f}%")
        print(f"  Precision: {metrics['precision']*100:.2f}%")
        print(f"  Recall:    {metrics['recall']*100:.2f}%")
        print(f"  F1-Score:  {metrics['f1_score']:.4f}")
        print(f"  ROC-AUC:   {metrics['roc_auc']:.4f}")
        print(f"  Confusion Matrix: {metrics['confusion_matrix']}")
        print(f"  Top 3 features: {list(metrics['feature_importances'].items())[:3]}")

    return metrics

if __name__ == "__main__":
    run_random_forest_benchmark()
