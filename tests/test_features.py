import pytest
import numpy as np
from src.features.feature_engineering import FeatureExtractor, FEATURE_NAMES

def test_feature_extraction_shape_and_names():
    """Verify that exactly 10 features are extracted for all 500 consumers."""
    fe = FeatureExtractor()
    df = fe.extract_all_features()
    assert len(df) == 500
    for name in FEATURE_NAMES:
        assert name in df.columns, f"Missing feature: {name}"

def test_feature_values_no_nans():
    """Verify that no extracted features contain NaN, null, or Inf values."""
    fe = FeatureExtractor()
    df = fe.extract_all_features()
    feature_matrix = df[FEATURE_NAMES].values
    assert not np.isnan(feature_matrix).any(), "Found NaN in feature matrix"
    assert not np.isinf(feature_matrix).any(), "Found Inf in feature matrix"

def test_feature_bounds():
    """Verify reasonable domain bounds for extracted features."""
    fe = FeatureExtractor()
    df = fe.extract_all_features()
    assert (df["mean_daily_consumption"] >= 0).all()
    assert (df["load_factor"] >= 0).all() and (df["load_factor"] <= 1.0).all()
    assert (df["missing_reading_pct"] >= 0).all() and (df["missing_reading_pct"] <= 100.0).all()

