"""
RESTful API Blueprint for Electricity Theft & Distribution Loss Detection.
Handles all backend data requests, status updates, exports, and pipeline triggers.
"""

from flask import Blueprint, jsonify, request, Response
from typing import Dict, Any

from config import Config
from database.db import query_db
from app.services.dashboard_service import DashboardService
from app.services.energy_service import EnergyService
from app.services.ml_service import MLService
from app.services.inspection_service import InspectionService
from src.simulation.generator import generate_complete_dataset
from src.models.isolation_forest import run_isolation_forest_pipeline
from src.models.random_forest import run_random_forest_benchmark

api_bp = Blueprint("api", __name__, url_prefix="/api")

# -------------------------------------------------------------
# Health Check
# -------------------------------------------------------------
@api_bp.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "HEALTHY",
        "service": "Electricity Theft & Distribution Loss Detection API",
        "project": Config.PROJECT_NAME,
        "version": "1.0.0"
    }), 200

# -------------------------------------------------------------
# Metadata Endpoints
# -------------------------------------------------------------
@api_bp.route("/feeders", methods=["GET"])
def get_feeders():
    """List all 5 distribution feeders with technical specs."""
    feeders = query_db("""
        SELECT feeder_id, name, substation_name, nominal_voltage_kv,
               conductor_resistance_ohm, length_km, created_at
        FROM feeders ORDER BY feeder_id
    """)
    return jsonify({"success": True, "feeders": feeders}), 200

@api_bp.route("/consumers", methods=["GET"])
def get_consumers():
    """List consumers with pagination, search, and feeder filter."""
    feeder_id = request.args.get("feeder_id")
    tariff = request.args.get("tariff")
    search = request.args.get("search")
    page = max(1, int(request.args.get("page", 1)))
    per_page = min(100, max(5, int(request.args.get("per_page", 20))))

    where_clauses = []
    params = []
    if feeder_id and feeder_id != "all":
        where_clauses.append("feeder_id = ?")
        params.append(feeder_id)
    if tariff and tariff != "all":
        where_clauses.append("tariff_category = ?")
        params.append(tariff)
    if search:
        where_clauses.append("(consumer_id LIKE ? OR meter_id LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    count_row = query_db(f"SELECT COUNT(*) as c FROM consumers {where_sql}", params, one=True)
    total = count_row["c"] if count_row else 0
    total_pages = (total + per_page - 1) // per_page

    offset = (page - 1) * per_page
    rows = query_db(
        f"""SELECT consumer_id, feeder_id, transformer_id, tariff_category,
                   sanctioned_load_kw, meter_id, simulation_scenario, created_at
            FROM consumers
            {where_sql}
            ORDER BY consumer_id
            LIMIT ? OFFSET ?""",
        params + [per_page, offset]
    )

    return jsonify({
        "success": True,
        "consumers": rows,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages
    }), 200

@api_bp.route("/consumers/<consumer_id>", methods=["GET"])
def get_consumer_detail(consumer_id: str):
    """Get single consumer full profile, engineered features, and time series."""
    detail = MLService.get_consumer_detail(consumer_id)
    if not detail:
        return jsonify({"success": False, "error": f"Consumer {consumer_id} not found."}), 404
    return jsonify({"success": True, "data": detail}), 200

# -------------------------------------------------------------
# Dashboard Endpoints
# -------------------------------------------------------------
@api_bp.route("/dashboard/summary", methods=["GET"])
def dashboard_summary():
    """8 primary KPI metrics for Executive Dashboard."""
    feeder_id = request.args.get("feeder_id")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    try:
        summary = DashboardService.get_summary(feeder_id, start_date, end_date)
        return jsonify({"success": True, "summary": summary}), 200
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to load dashboard summary: {str(e)}"}), 500

@api_bp.route("/dashboard/energy-trend", methods=["GET"])
def dashboard_trend():
    """Charts datasets for Executive Dashboard."""
    feeder_id = request.args.get("feeder_id")
    try:
        charts_data = DashboardService.get_charts_data(feeder_id)
        return jsonify({"success": True, "charts": charts_data}), 200
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to load dashboard charts: {str(e)}"}), 500

# -------------------------------------------------------------
# Energy Accounting Endpoints
# -------------------------------------------------------------
@api_bp.route("/energy-accounting", methods=["GET"])
def energy_accounting_summary():
    """Summary totals, feeder cards, and energy flow for accounting."""
    feeder_id = request.args.get("feeder_id")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    summary = EnergyService.get_accounting_summary(feeder_id, start_date, end_date)
    feeders = EnergyService.get_feeder_breakdown()
    flow = EnergyService.get_energy_flow_data()

    return jsonify({
        "success": True,
        "summary": summary,
        "feeders": feeders,
        "flow": flow
    }), 200

@api_bp.route("/energy-accounting/daily", methods=["GET"])
def energy_accounting_daily():
    """Daily audit records table with pagination and filters."""
    feeder_id = request.args.get("feeder_id")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    page = max(1, int(request.args.get("page", 1)))
    per_page = min(100, max(5, int(request.args.get("per_page", 15))))

    data = EnergyService.get_daily_accounting(feeder_id, start_date, end_date, page, per_page)
    return jsonify({"success": True, "data": data}), 200

# -------------------------------------------------------------
# AI Detection Endpoints
# -------------------------------------------------------------
@api_bp.route("/ai/predictions", methods=["GET"])
def ai_predictions():
    """Predictions list with review priority and diagnostic reasons."""
    feeder_id = request.args.get("feeder_id")
    tariff = request.args.get("tariff")
    priority = request.args.get("priority")
    search = request.args.get("search")
    sort_by = request.args.get("sort_by", "anomaly_score")
    sort_order = request.args.get("sort_order", "desc")
    page = max(1, int(request.args.get("page", 1)))
    per_page = min(100, max(5, int(request.args.get("per_page", 20))))

    data = MLService.get_predictions(
        feeder_id=feeder_id,
        tariff=tariff,
        priority=priority,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        per_page=per_page
    )
    return jsonify({"success": True, "data": data}), 200

@api_bp.route("/ai/metrics", methods=["GET"])
def ai_metrics():
    """Supervised benchmark evaluation metrics and feature importances."""
    analytics = MLService.get_analytics_data()
    return jsonify({"success": True, "metrics": analytics["metrics"]}), 200

@api_bp.route("/analytics", methods=["GET"])
def analytics_data():
    """All 8 analytics chart datasets."""
    data = MLService.get_analytics_data()
    return jsonify({"success": True, "analytics": data}), 200

# -------------------------------------------------------------
# Inspection Endpoints
# -------------------------------------------------------------
@api_bp.route("/inspection", methods=["GET"])
def inspection_worklist():
    """Inspection worklist items with filters and pagination."""
    feeder_id = request.args.get("feeder_id")
    priority = request.args.get("priority")
    status = request.args.get("status")
    search = request.args.get("search")
    sort_by = request.args.get("sort_by", "anomaly_score")
    sort_order = request.args.get("sort_order", "desc")
    page = max(1, int(request.args.get("page", 1)))
    per_page = min(100, max(5, int(request.args.get("per_page", 15))))

    data = InspectionService.get_worklist(
        feeder_id=feeder_id,
        priority=priority,
        status=status,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        per_page=per_page
    )
    return jsonify({"success": True, "data": data}), 200

@api_bp.route("/inspection/<inspection_id>", methods=["PUT"])
def update_inspection(inspection_id: str):
    """Update inspection status, remarks, or scheduled date."""
    body = request.get_json(silent=True) or {}
    status = body.get("inspection_status")
    remarks = body.get("remarks")
    scheduled_date = body.get("scheduled_date")
    inspected_by = body.get("inspected_by")

    result = InspectionService.update_inspection(
        inspection_id=inspection_id,
        status=status,
        remarks=remarks,
        scheduled_date=scheduled_date,
        inspected_by=inspected_by
    )

    if not result.get("success"):
        return jsonify(result), 400
    return jsonify(result), 200

# -------------------------------------------------------------
# CSV Export Endpoints
# -------------------------------------------------------------
@api_bp.route("/export/inspection", methods=["GET"])
def export_inspection_csv():
    """Download inspection worklist as CSV."""
    feeder_id = request.args.get("feeder_id")
    priority = request.args.get("priority")
    status = request.args.get("status")

    csv_data = InspectionService.export_worklist_csv(feeder_id, priority, status)
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=inspection_worklist.csv"}
    )

@api_bp.route("/export/energy", methods=["GET"])
def export_energy_csv():
    """Download daily energy accounting logs as CSV."""
    feeder_id = request.args.get("feeder_id")
    csv_data = EnergyService.export_daily_csv(feeder_id)
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=daily_energy_accounting.csv"}
    )

@api_bp.route("/export/predictions", methods=["GET"])
def export_predictions_csv():
    """Download ML predictions as CSV."""
    feeder_id = request.args.get("feeder_id")
    priority = request.args.get("priority")
    csv_data = MLService.export_predictions_csv(feeder_id, priority)
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=theft_predictions.csv"}
    )

# -------------------------------------------------------------
# Simulation and Training Pipeline Triggers
# -------------------------------------------------------------
@api_bp.route("/simulation/generate", methods=["POST"])
def trigger_simulation():
    """Regenerate synthetic dataset and re-run models."""
    try:
        stats = generate_complete_dataset(verbose=False)
        run_isolation_forest_pipeline(verbose=False)
        run_random_forest_benchmark(verbose=False)
        return jsonify({
            "success": True,
            "message": "Synthetic dataset successfully regenerated and models retrained.",
            "stats": stats
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@api_bp.route("/ai/train", methods=["POST"])
def trigger_training():
    """Retrain Isolation Forest and Random Forest benchmark."""
    try:
        df_preds = run_isolation_forest_pipeline(verbose=False)
        rf_metrics = run_random_forest_benchmark(verbose=False)
        return jsonify({
            "success": True,
            "message": "ML pipelines successfully retrained.",
            "metrics": rf_metrics
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@api_bp.route("/ai/predict", methods=["POST"])
def trigger_predict():
    """Recompute anomaly scores and classifications."""
    try:
        run_isolation_forest_pipeline(verbose=False)
        return jsonify({
            "success": True,
            "message": "Anomaly predictions updated successfully."
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

