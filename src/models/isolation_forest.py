"""
Isolation Forest Anomaly Detection Pipeline.

Unsupervised machine learning model for detecting anomalous electricity consumption patterns.
Scores are normalized to a consistent 0.0 - 1.0 range where 1.0 indicates highest anomaly.
Generates review priorities and actionable diagnostic explanations.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from typing import Dict, Any, Tuple, List, Optional

from config import Config
from database.db import get_db, query_db
from src.features.feature_engineering import FeatureExtractor, FEATURE_NAMES

class IsolationForestPipeline:
    def __init__(
        self,
        contamination: float = Config.IFOREST_CONTAMINATION,
        n_estimators: int = Config.IFOREST_N_ESTIMATORS,
        random_state: int = Config.RANDOM_SEED
    ):
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.random_state = random_state
        self.scaler = StandardScaler()
        self.model = IsolationForest(
            contamination=self.contamination,
            n_estimators=self.n_estimators,
            random_state=self.random_state,
            n_jobs=-1
        )
        self.min_neg_score = None
        self.max_neg_score = None
        self.is_fitted = False

    def fit_predict(self, X: np.ndarray, df: pd.DataFrame) -> pd.DataFrame:
        """
        Fit Isolation Forest and generate normalized anomaly scores [0, 1].
        """
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        self.is_fitted = True

        # In scikit-learn, decision_function returns:
        # positive for inliers, negative for outliers.
        raw_scores = self.model.decision_function(X_scaled)
        # Convert so higher raw value = more anomalous
        neg_scores = -raw_scores

        self.min_neg_score = float(np.min(neg_scores))
        self.max_neg_score = float(np.max(neg_scores))

        # Normalize strictly to [0.0, 1.0]
        denom = (self.max_neg_score - self.min_neg_score) if (self.max_neg_score > self.min_neg_score) else 1.0
        normalized_scores = (neg_scores - self.min_neg_score) / denom
        normalized_scores = np.clip(normalized_scores, 0.0, 1.0)

        # Binary anomaly label according to contamination (-1 = anomaly, 1 = normal)
        preds = self.model.predict(X_scaled)
        is_anomaly = (preds == -1).astype(int)

        df_out = df.copy()
        df_out["iforest_raw_score"] = raw_scores.round(4)
        df_out["anomaly_score"] = normalized_scores.round(4)
        df_out["is_anomaly"] = is_anomaly

        # Classify review priority based on strict rules:
        # Critical: [0.75, 1.00]
        # High:     [0.60, 0.74]
        # Medium:   [0.45, 0.59]
        # Low:      [0.00, 0.44]
        priorities = []
        diagnostic_reasons = []
        recommended_actions = []

        for idx, row in df_out.iterrows():
            score = row["anomaly_score"]
            priority, reason, action = self._diagnose_consumer(row, score)
            priorities.append(priority)
            diagnostic_reasons.append(reason)
            recommended_actions.append(action)

        df_out["review_priority"] = priorities
        df_out["diagnostic_reason"] = diagnostic_reasons
        df_out["recommended_action"] = recommended_actions

        return df_out

    def _diagnose_consumer(self, row: pd.Series, score: float) -> Tuple[str, str, str]:
        """Generate review priority, diagnostic explanation, and recommended action."""
        if score >= Config.PRIORITY_CRITICAL_MIN:
            priority = "Critical"
            action = "Immediate on-site technical inspection, meter seal integrity check, and secondary CT check within 24 hours."
        elif score >= Config.PRIORITY_HIGH_MIN:
            priority = "High"
            action = "Schedule field meter audit and review digital event logs for bypass or tampering within 3 business days."
        elif score >= Config.PRIORITY_MEDIUM_MIN:
            priority = "Medium"
            action = "Automated continuous AMR/AMI telemetry surveillance and cross-reference with historical seasonal trends."
        else:
            priority = "Low"
            action = "Standard routine automated monitoring. No immediate field inspection warranted."

        # Diagnostic reason generation from feature values
        reasons = []
        if row.get("drop_ratio", 1.0) < 0.45:
            pct = round((1.0 - row["drop_ratio"]) * 100, 1)
            reasons.append(f"Sharp {pct}% drop in recent 7-day consumption compared to baseline")

        if row.get("load_factor", 0.5) > 0.85 and row.get("cv_consumption", 0.5) < 0.05:
            reasons.append("Suspiciously flat/constant meter readings (meter flatline signature)")

        if row.get("peak_to_average_ratio", 1.0) < 0.35 and row.get("tariff_category") == "Residential":
            reasons.append("Abnormal absence of standard evening peak usage (18:00–22:00)")

        if row.get("peer_relative_deviation", 1.0) < 0.30:
            reasons.append(f"Consumption is {round(row['peer_relative_deviation']*100, 1)}% below feeder peer average")

        if row.get("missing_reading_pct", 0.0) > 12.0:
            reasons.append(f"High telemetry dropout rate ({round(row['missing_reading_pct'], 1)}% missed intervals)")

        if not reasons:
            if score >= 0.50:
                reasons.append("Multivariate deviation from normative consumption profile")
            else:
                reasons.append("Normal consumption pattern consistent with tariff class baseline")

        reason_str = "; ".join(reasons)
        return priority, reason_str, action

    def save(self, model_path: Optional[Path] = None):
        """Save model and scaler using Joblib."""
        path = model_path or Config.IFOREST_MODEL_PATH
        os.makedirs(os.path.dirname(path), exist_ok=True)
        joblib.dump({
            "model": self.model,
            "scaler": self.scaler,
            "min_neg_score": self.min_neg_score,
            "max_neg_score": self.max_neg_score,
            "contamination": self.contamination,
            "n_estimators": self.n_estimators,
            "feature_names": FEATURE_NAMES
        }, path)

    @classmethod
    def load(cls, model_path: Optional[Path] = None) -> "IsolationForestPipeline":
        """Load trained model from disk."""
        path = model_path or Config.IFOREST_MODEL_PATH
        data = joblib.load(path)
        instance = cls(
            contamination=data["contamination"],
            n_estimators=data["n_estimators"]
        )
        instance.model = data["model"]
        instance.scaler = data["scaler"]
        instance.min_neg_score = data["min_neg_score"]
        instance.max_neg_score = data["max_neg_score"]
        instance.is_fitted = True
        return instance

def run_isolation_forest_pipeline(verbose: bool = True) -> pd.DataFrame:
    """
    Extract features, train Isolation Forest, save predictions to SQLite, and populate inspection records.
    """
    if verbose:
        print("Extracting features for 500 consumers...")
    extractor = FeatureExtractor()
    df_features = extractor.extract_all_features()
    X, consumer_ids, df = extractor.get_feature_matrix(df_features)

    if verbose:
        print(f"Training Isolation Forest (n_estimators={Config.IFOREST_N_ESTIMATORS}, contamination={Config.IFOREST_CONTAMINATION})...")
    pipeline = IsolationForestPipeline()
    df_preds = pipeline.fit_predict(X, df)
    pipeline.save()

    if verbose:
        print("Saving predictions and inspection records to SQLite database...")

    # Save to SQLite
    with get_db() as conn:
        conn.execute("DELETE FROM theft_predictions;")
        conn.execute("DELETE FROM inspection_records;")

        # Insert theft predictions (all 500 consumers)
        prediction_rows = []
        for _, r in df_preds.iterrows():
            prediction_rows.append((
                r["consumer_id"],
                r["feeder_id"],
                r["tariff_category"],
                float(r["iforest_raw_score"]),
                float(r["anomaly_score"]),
                int(r["is_anomaly"]),
                r["review_priority"],
                None,  # rf_probability updated later by benchmark model
                r["diagnostic_reason"],
                r["recommended_action"]
            ))

        conn.executemany(
            """INSERT INTO theft_predictions (consumer_id, feeder_id, tariff_category, iforest_raw_score,
                                              anomaly_score, is_anomaly, review_priority, rf_probability,
                                              diagnostic_reason, recommended_action)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            prediction_rows
        )

        # Inspection Worklist Candidates: Critical, High, and Medium review priority consumers
        # Per prompt: "Only consumers requiring investigation should be marked as inspection candidates."
        inspection_candidates = df_preds[df_preds["review_priority"].isin(["Critical", "High", "Medium"])]
        inspection_rows = []
        for idx, (_, r) in enumerate(inspection_candidates.iterrows()):
            insp_id = f"INSP-{idx+1:04d}"
            inspection_rows.append((
                insp_id,
                r["consumer_id"],
                r["feeder_id"],
                r["tariff_category"],
                float(r["sanctioned_load_kw"]),
                float(r["mean_daily_consumption"]),
                float(r["anomaly_score"]),
                r["review_priority"],
                r["diagnostic_reason"],
                r["recommended_action"],
                "Pending",
                "",  # remarks
                None,  # scheduled_date
                None   # inspected_by
            ))

        conn.executemany(
            """INSERT INTO inspection_records (inspection_id, consumer_id, feeder_id, tariff_category,
                                               sanctioned_load_kw, mean_daily_consumption, anomaly_score,
                                               priority, diagnostic_reason, recommended_action,
                                               inspection_status, remarks, scheduled_date, inspected_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            inspection_rows
        )

    if verbose:
        print(f"Predictions stored: {len(prediction_rows)} consumers.")
        print(f"Inspection candidates created: {len(inspection_rows)} consumers (Critical/High/Medium).")
        print(f"Priority breakdown:\n{df_preds['review_priority'].value_counts()}")

    return df_preds

if __name__ == "__main__":
    run_isolation_forest_pipeline()

