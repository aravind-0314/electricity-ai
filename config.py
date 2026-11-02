import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent

# Load .env file
load_dotenv(BASE_DIR / ".env")

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "default-dev-secret-key-ssiet-ads-2026")
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
    PORT = int(os.getenv("PORT", 5000))
    HOST = os.getenv("HOST", "0.0.0.0")

    # Database
    DATABASE_PATH = BASE_DIR / os.getenv("DATABASE_PATH", "database/grid_loss_system.db")

    # Simulation Parameters
    RANDOM_SEED = int(os.getenv("RANDOM_SEED", 42))
    SIMULATION_DAYS = int(os.getenv("SIMULATION_DAYS", 30))
    READINGS_PER_DAY = 24
    TOTAL_HOURS = SIMULATION_DAYS * READINGS_PER_DAY  # 720
    CONSUMER_COUNT = int(os.getenv("CONSUMER_COUNT", 500))
    FEEDER_COUNT = int(os.getenv("FEEDER_COUNT", 5))

    # Physics Constants (clearly identified as engineering simulation assumptions)
    NOMINAL_VOLTAGE_KV = 11.0  # 11 kV medium voltage distribution
    SYSTEM_POWER_FACTOR = 0.92  # Typical commercial/residential distribution power factor
    FEEDER_RESISTANCE_OHM_PER_KM = 0.35  # ACSR Dog/Rabbit conductor ~0.35 ohm/km
    DEFAULT_FEEDER_LENGTH_KM = 3.5  # average length
    TRANSFORMER_CORE_LOSS_FACTOR = 0.003  # ~0.3% of rated capacity
    TRANSFORMER_COPPER_LOSS_FACTOR = 0.012  # ~1.2% at full load

    # Machine Learning Settings
    IFOREST_CONTAMINATION = 0.12  # Expected anomaly rate
    IFOREST_N_ESTIMATORS = 150
    RF_N_ESTIMATORS = 120
    RF_TEST_SIZE = 0.30

    # Review Priority Thresholds (Normalized 0.0 - 1.0)
    PRIORITY_CRITICAL_MIN = 0.75
    PRIORITY_HIGH_MIN = 0.60
    PRIORITY_MEDIUM_MIN = 0.45

    # Paths
    MODELS_DIR = BASE_DIR / "models"
    EXPORTS_DIR = BASE_DIR / "exports"
    IFOREST_MODEL_PATH = MODELS_DIR / "isolation_forest.joblib"
    RF_MODEL_PATH = MODELS_DIR / "random_forest.joblib"
    METRICS_PATH = MODELS_DIR / "metrics.json"

    # Academic metadata
    PROJECT_NAME = "AI-Based Electricity Theft and Distribution Loss Detection Using Machine Learning"
    PROJECT_SHORT_NAME = "Electricity Theft & Distribution Loss Detection"
    PROJECT_SUBTITLE = "Smart Grid Intelligence & Distribution Loss Monitoring"
    COLLEGE = "Sri Shakthi Institute of Engineering and Technology"
    DEPARTMENT = "Artificial Intelligence and Data Science"
    PROJECT_GUIDE = "Mrs. Dr. Kamalaveni"

