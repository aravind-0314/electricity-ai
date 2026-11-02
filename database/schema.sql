-- Database Schema for Electricity Theft & Distribution Loss Detection
-- SQLite 3 Database

PRAGMA foreign_keys = ON;

-- 1. Feeders
CREATE TABLE IF NOT EXISTS feeders (
    feeder_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    substation_name TEXT NOT NULL,
    nominal_voltage_kv REAL NOT NULL DEFAULT 11.0,
    conductor_resistance_ohm REAL NOT NULL,
    length_km REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Transformers
CREATE TABLE IF NOT EXISTS transformers (
    transformer_id TEXT PRIMARY KEY,
    feeder_id TEXT NOT NULL,
    capacity_kva REAL NOT NULL,
    core_loss_kw REAL NOT NULL,
    rated_copper_loss_kw REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (feeder_id) REFERENCES feeders(feeder_id) ON DELETE CASCADE
);

-- 3. Consumers
CREATE TABLE IF NOT EXISTS consumers (
    consumer_id TEXT PRIMARY KEY,
    feeder_id TEXT NOT NULL,
    transformer_id TEXT NOT NULL,
    tariff_category TEXT NOT NULL CHECK (tariff_category IN ('Residential', 'Commercial', 'Agricultural')),
    sanctioned_load_kw REAL NOT NULL,
    meter_id TEXT UNIQUE NOT NULL,
    simulation_scenario TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (feeder_id) REFERENCES feeders(feeder_id) ON DELETE CASCADE,
    FOREIGN KEY (transformer_id) REFERENCES transformers(transformer_id) ON DELETE CASCADE
);

-- 4. Consumer Hourly Readings (360,000 records)
CREATE TABLE IF NOT EXISTS consumer_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    consumer_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    day_number INTEGER NOT NULL,
    hour INTEGER NOT NULL,
    actual_consumption_kwh REAL NOT NULL,
    billed_consumption_kwh REAL NOT NULL,
    meter_status TEXT NOT NULL DEFAULT 'NORMAL',
    FOREIGN KEY (consumer_id) REFERENCES consumers(consumer_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_cr_consumer_time ON consumer_readings(consumer_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_cr_day_hour ON consumer_readings(day_number, hour);
CREATE INDEX IF NOT EXISTS idx_cr_consumer_day ON consumer_readings(consumer_id, day_number);

-- 5. Feeder Hourly Readings (3,600 records)
CREATE TABLE IF NOT EXISTS feeder_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feeder_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    day_number INTEGER NOT NULL,
    hour INTEGER NOT NULL,
    supplied_energy_kwh REAL NOT NULL,
    total_billed_kwh REAL NOT NULL,
    cable_loss_kwh REAL NOT NULL,
    transformer_core_loss_kwh REAL NOT NULL,
    transformer_copper_loss_kwh REAL NOT NULL,
    technical_loss_kwh REAL NOT NULL,
    unexplained_loss_kwh REAL NOT NULL,
    loss_percentage REAL NOT NULL,
    FOREIGN KEY (feeder_id) REFERENCES feeders(feeder_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_fr_feeder_time ON feeder_readings(feeder_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_fr_day_hour ON feeder_readings(day_number, hour);

-- 6. Loss Audit Logs (150 daily feeder audit records)
CREATE TABLE IF NOT EXISTS loss_audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_date TEXT NOT NULL,
    feeder_id TEXT NOT NULL,
    day_number INTEGER NOT NULL,
    supplied_energy_kwh REAL NOT NULL,
    billed_energy_kwh REAL NOT NULL,
    cable_loss_kwh REAL NOT NULL,
    transformer_core_loss_kwh REAL NOT NULL,
    transformer_copper_loss_kwh REAL NOT NULL,
    technical_loss_kwh REAL NOT NULL,
    unexplained_loss_kwh REAL NOT NULL,
    total_distribution_loss_kwh REAL NOT NULL,
    loss_percentage REAL NOT NULL,
    reconciliation_residual_kwh REAL NOT NULL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(audit_date, feeder_id),
    FOREIGN KEY (feeder_id) REFERENCES feeders(feeder_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_lal_feeder ON loss_audit_logs(feeder_id);
CREATE INDEX IF NOT EXISTS idx_lal_date ON loss_audit_logs(audit_date);

-- 7. Theft Predictions (500 records)
CREATE TABLE IF NOT EXISTS theft_predictions (
    consumer_id TEXT PRIMARY KEY,
    feeder_id TEXT NOT NULL,
    tariff_category TEXT NOT NULL,
    iforest_raw_score REAL NOT NULL,
    anomaly_score REAL NOT NULL,
    is_anomaly INTEGER NOT NULL DEFAULT 0,
    review_priority TEXT NOT NULL CHECK (review_priority IN ('Critical', 'High', 'Medium', 'Low')),
    rf_probability REAL,
    diagnostic_reason TEXT NOT NULL,
    recommended_action TEXT NOT NULL,
    predicted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (consumer_id) REFERENCES consumers(consumer_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tp_priority ON theft_predictions(review_priority);
CREATE INDEX IF NOT EXISTS idx_tp_score ON theft_predictions(anomaly_score);
CREATE INDEX IF NOT EXISTS idx_tp_feeder ON theft_predictions(feeder_id);

-- 8. Model Evaluation Metrics
CREATE TABLE IF NOT EXISTS model_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_name TEXT NOT NULL,
    accuracy REAL,
    precision REAL,
    recall REAL,
    f1_score REAL,
    roc_auc REAL,
    confusion_matrix_json TEXT,
    feature_importance_json TEXT,
    evaluation_notes TEXT,
    trained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. Inspection Worklist Records
CREATE TABLE IF NOT EXISTS inspection_records (
    inspection_id TEXT PRIMARY KEY,
    consumer_id TEXT NOT NULL UNIQUE,
    feeder_id TEXT NOT NULL,
    tariff_category TEXT NOT NULL,
    sanctioned_load_kw REAL NOT NULL,
    mean_daily_consumption REAL NOT NULL,
    anomaly_score REAL NOT NULL,
    priority TEXT NOT NULL CHECK (priority IN ('Critical', 'High', 'Medium', 'Low')),
    diagnostic_reason TEXT NOT NULL,
    recommended_action TEXT NOT NULL,
    inspection_status TEXT NOT NULL DEFAULT 'Pending' CHECK (inspection_status IN ('Pending', 'Scheduled', 'In Progress', 'Completed', 'Not Suspicious After Verification')),
    remarks TEXT DEFAULT '',
    scheduled_date TEXT,
    inspected_by TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (consumer_id) REFERENCES consumers(consumer_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ir_status ON inspection_records(inspection_status);
CREATE INDEX IF NOT EXISTS idx_ir_priority ON inspection_records(priority);

-- 10. System Settings & Configuration
CREATE TABLE IF NOT EXISTS system_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

