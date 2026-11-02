import pytest
from database.db import query_db, get_connection

def test_database_connection():
    """Verify database connection and foreign key pragma."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys;")
    res = cur.fetchone()[0]
    conn.close()
    assert res == 1

def test_required_table_counts():
    """
    Verify exact dataset size requirements:
    - Exactly 5 Feeders
    - Exactly 5 Transformers
    - Exactly 500 Consumers
    - Exactly 360,000 Consumer Hourly Readings
    - Exactly 3,600 Feeder Hourly Readings
    - Exactly 150 Daily Feeder Audit Records
    - Exactly 500 Theft Predictions
    """
    feeders = query_db("SELECT COUNT(*) as c FROM feeders", one=True)["c"]
    transformers = query_db("SELECT COUNT(*) as c FROM transformers", one=True)["c"]
    consumers = query_db("SELECT COUNT(*) as c FROM consumers", one=True)["c"]
    cr = query_db("SELECT COUNT(*) as c FROM consumer_readings", one=True)["c"]
    fr = query_db("SELECT COUNT(*) as c FROM feeder_readings", one=True)["c"]
    audit = query_db("SELECT COUNT(*) as c FROM loss_audit_logs", one=True)["c"]
    preds = query_db("SELECT COUNT(*) as c FROM theft_predictions", one=True)["c"]

    assert feeders == 5, f"Expected 5 feeders, got {feeders}"
    assert transformers == 5, f"Expected 5 transformers, got {transformers}"
    assert consumers == 500, f"Expected 500 consumers, got {consumers}"
    assert cr == 360000, f"Expected 360,000 consumer readings, got {cr}"
    assert fr == 3600, f"Expected 3,600 feeder readings, got {fr}"
    assert audit == 150, f"Expected 150 daily audit logs, got {audit}"
    assert preds == 500, f"Expected 500 predictions, got {preds}"

def test_consumer_categories():
    """Verify that all consumer tariff categories are valid."""
    tariffs = query_db("SELECT DISTINCT tariff_category FROM consumers")
    categories = {t["tariff_category"] for t in tariffs}
    assert categories.issubset({"Residential", "Commercial", "Agricultural"})

def test_system_settings_seeded():
    """Verify system settings are present."""
    settings = query_db("SELECT COUNT(*) as c FROM system_settings", one=True)["c"]
    assert settings >= 5

