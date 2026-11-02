"""
Main Page Routes Blueprint for Electricity Theft & Distribution Loss Detection.
Renders all five frontend pages.
"""

from flask import Blueprint, render_template, redirect, url_for
from config import Config
from database.db import query_db

main_bp = Blueprint("main", __name__)

@main_bp.context_processor
def inject_global_metadata():
    """Inject academic project information into all templates."""
    return {
        "project_name": Config.PROJECT_NAME,
        "project_short_name": Config.PROJECT_SHORT_NAME,
        "project_subtitle": Config.PROJECT_SUBTITLE,
        "college": Config.COLLEGE,
        "department": Config.DEPARTMENT,
        "project_guide": Config.PROJECT_GUIDE
    }

@main_bp.route("/")
def index():
    """Redirect root to executive dashboard."""
    return redirect(url_for("main.dashboard"))

@main_bp.route("/dashboard")
def dashboard():
    """PAGE 1: Executive Dashboard."""
    feeders = query_db("SELECT feeder_id, name FROM feeders ORDER BY feeder_id")
    return render_template("dashboard.html", active_page="dashboard", feeders=feeders)

@main_bp.route("/energy-accounting")
def energy_accounting():
    """PAGE 2: Energy Accounting."""
    feeders = query_db("SELECT feeder_id, name FROM feeders ORDER BY feeder_id")
    return render_template("energy_accounting.html", active_page="energy_accounting", feeders=feeders)

@main_bp.route("/ai-detection")
def ai_detection():
    """PAGE 3: AI Theft Detection."""
    feeders = query_db("SELECT feeder_id, name FROM feeders ORDER BY feeder_id")
    return render_template("ai_detection.html", active_page="ai_detection", feeders=feeders)

@main_bp.route("/analytics")
def analytics():
    """PAGE 4: Analytics and Insights."""
    return render_template("analytics.html", active_page="analytics")

@main_bp.route("/inspection")
def inspection():
    """PAGE 5: Inspection Worklist."""
    feeders = query_db("SELECT feeder_id, name FROM feeders ORDER BY feeder_id")
    return render_template("inspection.html", active_page="inspection", feeders=feeders)

