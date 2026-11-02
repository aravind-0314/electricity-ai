"""
Reset script to wipe and regenerate the synthetic dataset and retrain models.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.db import reset_db
from src.simulation.generator import generate_complete_dataset
from src.models.isolation_forest import run_isolation_forest_pipeline
from src.models.random_forest import run_random_forest_benchmark

def main():
    print("=" * 60)
    print(" Electricity Theft & Distribution Loss Detection - Complete Reset")
    print("=" * 60)
    print("1. Re-initializing SQLite database...")
    reset_db()
    print("2. Generating synthetic 500-consumer 30-day dataset...")
    generate_complete_dataset(verbose=True)
    print("3. Training Isolation Forest pipeline...")
    run_isolation_forest_pipeline(verbose=True)
    print("4. Training Random Forest benchmark...")
    run_random_forest_benchmark(verbose=True)
    print("=" * 60)
    print(" Database & ML pipeline completely reset and re-synchronized!")
    print("=" * 60)

if __name__ == "__main__":
    main()

