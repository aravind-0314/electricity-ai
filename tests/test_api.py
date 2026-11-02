import pytest
import json
from app import create_app
from database.db import query_db

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_health_endpoint(client):
    """Test GET /api/health."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "HEALTHY"

def test_dashboard_summary_api(client):
    """Test GET /api/dashboard/summary and energy-trend with all and specific feeders."""
    res = client.get("/api/dashboard/summary")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["summary"]["total_consumers"] == 500
    assert data["summary"]["total_feeders"] == 5
    assert data["summary"]["total_electricity_supplied_kwh"] > 0
    assert data["summary"]["overall_loss_percentage"] > 0

    # Verify feeder filtering on both summary and energy-trend endpoints
    for f in ["all", "FDR-01", "FDR-05", "INVALID"]:
        s_res = client.get(f"/api/dashboard/summary?feeder_id={f}")
        assert s_res.status_code == 200
        assert s_res.get_json()["success"] is True

        t_res = client.get(f"/api/dashboard/energy-trend?feeder_id={f}")
        assert t_res.status_code == 200
        assert t_res.get_json()["success"] is True

def test_energy_accounting_api(client):
    """Test GET /api/energy-accounting and daily table."""
    res = client.get("/api/energy-accounting")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "summary" in data
    assert "feeders" in data
    assert len(data["feeders"]) == 5

    res_daily = client.get("/api/energy-accounting/daily?page=1&per_page=10")
    assert res_daily.status_code == 200
    d_data = res_daily.get_json()
    assert d_data["data"]["total_records"] == 150

def test_ai_predictions_api(client):
    """Test GET /api/ai/predictions."""
    res = client.get("/api/ai/predictions?page=1&per_page=10")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["data"]["total_records"] == 500

def test_inspection_status_update(client):
    """Test PUT /api/inspection/<inspection_id> persistence."""
    # Find one inspection record
    rec = query_db("SELECT inspection_id FROM inspection_records LIMIT 1", one=True)
    assert rec is not None
    insp_id = rec["inspection_id"]

    # Update to 'Scheduled'
    payload = {
        "inspection_status": "Scheduled",
        "inspected_by": "Er. Tests Team",
        "remarks": "Automated pytest verification inspection"
    }
    put_res = client.put(f"/api/inspection/{insp_id}", json=payload)
    assert put_res.status_code == 200
    data = put_res.get_json()
    assert data["success"] is True
    assert data["record"]["inspection_status"] == "Scheduled"
    assert data["record"]["inspected_by"] == "Er. Tests Team"

    # Verify directly in SQLite
    in_db = query_db("SELECT inspection_status, inspected_by FROM inspection_records WHERE inspection_id = ?", (insp_id,), one=True)
    assert in_db["inspection_status"] == "Scheduled"
    assert in_db["inspected_by"] == "Er. Tests Team"

def test_csv_exports(client):
    """Test CSV export endpoints."""
    # Inspection CSV
    res_insp = client.get("/api/export/inspection")
    assert res_insp.status_code == 200
    assert "text/csv" in res_insp.content_type
    assert b"Consumer ID" in res_insp.data

    # Energy CSV
    res_energy = client.get("/api/export/energy")
    assert res_energy.status_code == 200
    assert "text/csv" in res_energy.content_type
    assert b"Supplied Energy" in res_energy.data

