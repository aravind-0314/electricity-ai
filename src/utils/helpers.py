"""
Utility functions and pipeline orchestration for Electricity Theft & Distribution Loss Detection.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from typing import Dict, Any
from database.db import init_db, query_db
from src.simulation.generator import generate_complete_dataset
from src.features.feature_engineering import FeatureExtractor
from src.models.isolation_forest import run_isolation_forest_pipeline
from src.models.random_forest import run_random_forest_benchmark

def ensure_initialized(force_regenerate: bool = False) -> Dict[str, Any]:
    """
    Ensure SQLite database is created, dataset exists, and ML models are trained.
    If database has 0 consumers or force_regenerate is True, runs generation and training.
    """
    init_db()

    # Check existing counts
    cons_count = query_db("SELECT COUNT(*) as c FROM consumers", one=True)
    needs_data = force_regenerate or (not cons_count) or (cons_count["c"] < 500)

    stats = {}
    if needs_data:
        stats = generate_complete_dataset(verbose=True)
        run_isolation_forest_pipeline(verbose=True)
        run_random_forest_benchmark(verbose=True)
    else:
        # Check if predictions exist
        preds_count = query_db("SELECT COUNT(*) as c FROM theft_predictions", one=True)
        if not preds_count or preds_count["c"] < 500:
            run_isolation_forest_pipeline(verbose=True)
            run_random_forest_benchmark(verbose=True)

    return stats

