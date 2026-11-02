"""
Feature Engineering Module for Electricity Consumption Anomaly Detection.

Extracts 10 consumer-level features:
1. mean_daily_consumption: Average daily consumption in kWh over the 30-day period.
2. rolling_avg_7d: Average daily consumption over the recent 7 days (days 24 to 30).
3. consumption_std: Standard deviation of daily consumption.
4. cv_consumption: Coefficient of variation (std / mean) - captures consumption volatility.
5. drop_ratio: Ratio of recent 7-day average to previous 23-day baseline average.
6. hourly_variability: Average hourly variance across 24 intervals.
7. load_factor: Ratio of average hourly consumption to maximum hourly peak load (mean / max).
8. peak_to_average_ratio: Ratio of evening peak (18:00 - 22:00) usage to overall hourly average.
9. missing_reading_pct: Percentage of missing/zero/dropout readings.
10. peer_relative_deviation: Consumer's daily consumption relative to the average of peers in the same tariff category on the same feeder.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from typing import List, Dict, Tuple, Optional, Any
import numpy as np
import pandas as pd
from database.db import get_connection

FEATURE_NAMES = [
    "mean_daily_consumption",
    "rolling_avg_7d",
    "consumption_std",
    "cv_consumption",
    "drop_ratio",
    "hourly_variability",
    "load_factor",
    "peak_to_average_ratio",
    "missing_reading_pct",
    "peer_relative_deviation"
]

class FeatureExtractor:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def extract_all_features(self) -> pd.DataFrame:
        """
        Extract all 10 features for all 500 consumers using optimized SQL aggregations.
        Returns a pandas DataFrame indexed by consumer_id with columns FEATURE_NAMES
        plus metadata (feeder_id, tariff_category, sanctioned_load_kw, simulation_scenario).
        """
        conn = get_connection(self.db_path)
        try:
            # 1. Load consumer metadata
            consumers_df = pd.read_sql_query(
                """SELECT consumer_id, feeder_id, tariff_category, sanctioned_load_kw, simulation_scenario
                   FROM consumers ORDER BY consumer_id""",
                conn
            )

            # 2. Daily consumption per consumer
            daily_df = pd.read_sql_query(
                """SELECT consumer_id, day_number,
                          SUM(billed_consumption_kwh) as daily_kwh,
                          COUNT(*) as total_readings,
                          SUM(CASE WHEN meter_status = 'DROPOUT' OR billed_consumption_kwh = 0 THEN 1 ELSE 0 END) as zero_or_dropout_count
                   FROM consumer_readings
                   GROUP BY consumer_id, day_number
                   ORDER BY consumer_id, day_number""",
                conn
            )

            # 3. Hourly metrics per consumer
            hourly_metrics_df = pd.read_sql_query(
                """SELECT consumer_id,
                          AVG(billed_consumption_kwh) as mean_hourly,
                          MAX(billed_consumption_kwh) as max_hourly,
                          AVG(CASE WHEN hour BETWEEN 18 AND 22 THEN billed_consumption_kwh ELSE NULL END) as peak_evening_avg
                   FROM consumer_readings
                   GROUP BY consumer_id""",
                conn
            )

            # 4. Hourly variance per consumer across the 24 hours of the day
            hourly_variance_df = pd.read_sql_query(
                """SELECT consumer_id, hour, AVG(billed_consumption_kwh) as avg_by_hour
                   FROM consumer_readings
                   GROUP BY consumer_id, hour""",
                conn
            )

        finally:
            conn.close()

        # Compute daily stats per consumer
        # Mean daily, std, cv
        daily_stats = daily_df.groupby("consumer_id")["daily_kwh"].agg(["mean", "std"]).reset_index()
        daily_stats = daily_stats.rename(columns={"mean": "mean_daily_consumption", "std": "consumption_std"})
        daily_stats["consumption_std"] = daily_stats["consumption_std"].fillna(0.0)

        # CV = std / mean
        daily_stats["cv_consumption"] = np.where(
            daily_stats["mean_daily_consumption"] > 1e-4,
            daily_stats["consumption_std"] / daily_stats["mean_daily_consumption"],
            0.0
        )

        # Rolling 7-day average (days 24 to 30)
        recent_7d = daily_df[daily_df["day_number"] >= 24].groupby("consumer_id")["daily_kwh"].mean().reset_index()
        recent_7d = recent_7d.rename(columns={"daily_kwh": "rolling_avg_7d"})

        # First 23 days baseline average
        baseline_23d = daily_df[daily_df["day_number"] < 24].groupby("consumer_id")["daily_kwh"].mean().reset_index()
        baseline_23d = baseline_23d.rename(columns={"daily_kwh": "baseline_avg_23d"})

        # Merge daily parts
        df = consumers_df.merge(daily_stats, on="consumer_id", how="left")
        df = df.merge(recent_7d, on="consumer_id", how="left")
        df = df.merge(baseline_23d, on="consumer_id", how="left")

        # drop_ratio = rolling_avg_7d / max(0.01, baseline_avg_23d)
        baseline_safe = np.maximum(df["baseline_avg_23d"].fillna(1.0), 0.05)
        df["drop_ratio"] = df["rolling_avg_7d"].fillna(0.0) / baseline_safe
        # Cap extreme ratios
        df["drop_ratio"] = df["drop_ratio"].clip(0.0, 5.0)

        # Hourly variability: std dev across the 24 average hourly bins
        hourly_var = hourly_variance_df.groupby("consumer_id")["avg_by_hour"].std().reset_index()
        hourly_var = hourly_var.rename(columns={"avg_by_hour": "hourly_variability"})
        hourly_var["hourly_variability"] = hourly_var["hourly_variability"].fillna(0.0)
        df = df.merge(hourly_var, on="consumer_id", how="left")

        # Load factor and peak-to-average ratio
        df = df.merge(hourly_metrics_df, on="consumer_id", how="left")
        max_safe = np.maximum(df["max_hourly"].fillna(0.1), 0.05)
        df["load_factor"] = (df["mean_hourly"].fillna(0.0) / max_safe).clip(0.0, 1.0)

        mean_hourly_safe = np.maximum(df["mean_hourly"].fillna(0.1), 0.01)
        df["peak_to_average_ratio"] = (df["peak_evening_avg"].fillna(0.0) / mean_hourly_safe).clip(0.0, 10.0)

        # Missing reading percentage (over all 720 hours)
        dropout_sum = daily_df.groupby("consumer_id")["zero_or_dropout_count"].sum().reset_index()
        total_readings = daily_df.groupby("consumer_id")["total_readings"].sum().reset_index()
        dropout_df = dropout_sum.merge(total_readings, on="consumer_id")
        dropout_df["missing_reading_pct"] = (dropout_df["zero_or_dropout_count"] / dropout_df["total_readings"]) * 100.0
        df = df.merge(dropout_df[["consumer_id", "missing_reading_pct"]], on="consumer_id", how="left")

        # Peer relative deviation:
        # Consumer mean daily vs mean of peers with the same tariff on the same feeder
        peer_means = df.groupby(["feeder_id", "tariff_category"])["mean_daily_consumption"].transform("mean")
        peer_safe = np.maximum(peer_means, 0.1)
        # Deviation ratio: consumer_mean / peer_mean
        df["peer_relative_deviation"] = (df["mean_daily_consumption"] / peer_safe).clip(0.0, 5.0)

        # Fill any remaining NaNs with 0.0
        for col in FEATURE_NAMES:
            df[col] = df[col].fillna(0.0).round(4)

        return df

    def get_feature_matrix(self, df: Optional[pd.DataFrame] = None) -> Tuple[np.ndarray, List[str], pd.DataFrame]:
        """
        Returns feature numpy array (500 x 10), consumer IDs list, and full DataFrame.
        """
        if df is None:
            df = self.extract_all_features()
        X = df[FEATURE_NAMES].values.astype(np.float64)
        consumer_ids = df["consumer_id"].tolist()
        return X, consumer_ids, df
