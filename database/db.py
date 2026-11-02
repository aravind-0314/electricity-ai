import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager
from config import Config

DB_PATH = Path(Config.DATABASE_PATH)

def get_connection(db_path=None):
    """Create a new SQLite connection with foreign keys and dict-like row factory."""
    path = db_path or DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, timeout=30.0)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")  # Fast concurrent reads/writes
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.row_factory = sqlite3.Row
    return conn

@contextmanager
def get_db(db_path=None):
    """Context manager for SQLite database operations with auto-commit/rollback."""
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db(db_path=None):
    """Initialize database tables and default system settings using schema.sql."""
    schema_path = Path(__file__).resolve().parent / "schema.sql"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    with get_db(db_path) as conn:
        conn.executescript(schema_sql)
        # Seed default system settings
        default_settings = [
            ("system_status", "ONLINE", "Overall system operational status"),
            ("last_simulation_run", "", "Timestamp of last simulation run"),
            ("last_model_train", "", "Timestamp of last model training"),
            ("reconciliation_tolerance_kwh", "0.01", "Acceptable residual tolerance in kWh"),
            ("critical_threshold", str(Config.PRIORITY_CRITICAL_MIN), "Threshold for Critical review priority"),
            ("high_threshold", str(Config.PRIORITY_HIGH_MIN), "Threshold for High review priority"),
            ("medium_threshold", str(Config.PRIORITY_MEDIUM_MIN), "Threshold for Medium review priority"),
        ]
        conn.executemany(
            """INSERT OR IGNORE INTO system_settings (key, value, description)
               VALUES (?, ?, ?)""",
            default_settings
        )
    return True

def query_db(query, args=(), one=False, db_path=None):
    """Execute a SELECT query and return rows as list of dicts or single dict."""
    with get_db(db_path) as conn:
        cur = conn.cursor()
        cur.execute(query, args)
        rv = cur.fetchall()
        cur.close()
        if not rv:
            return None if one else []
        return dict(rv[0]) if one else [dict(row) for row in rv]

def execute_db(query, args=(), db_path=None):
    """Execute an INSERT/UPDATE/DELETE query and return lastrowid and rowcount."""
    with get_db(db_path) as conn:
        cur = conn.cursor()
        cur.execute(query, args)
        lastrowid = cur.lastrowid
        rowcount = cur.rowcount
        cur.close()
        return {"lastrowid": lastrowid, "rowcount": rowcount}

def executemany_db(query, seq_of_args, db_path=None):
    """Execute batch INSERT/UPDATE in a single transaction."""
    with get_db(db_path) as conn:
        cur = conn.cursor()
        cur.executemany(query, seq_of_args)
        rowcount = cur.rowcount
        cur.close()
        return rowcount

def reset_db(db_path=None):
    """Drop and recreate all tables safely."""
    path = db_path or DB_PATH
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass
    return init_db(path)

