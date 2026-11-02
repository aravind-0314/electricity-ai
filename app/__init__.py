"""
Flask Application Factory for Electricity Theft & Distribution Loss Detection.
"""

from flask import Flask, jsonify, render_template, request
from config import Config
from app.routes.main import main_bp
from app.routes.api import api_bp
from src.utils.helpers import ensure_initialized

def create_app(config_class=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure database, data, and models exist
    with app.app_context():
        ensure_initialized(force_regenerate=False)
        try:
            from app.services.ml_service import MLService
            MLService.get_features_df()
        except Exception:
            pass

    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "API route not found."}), 404
        return render_template("base.html", error_title="404 - Page Not Found", error_message="The requested route does not exist."), 404

    @app.errorhandler(500)
    def internal_error(error):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Internal server error occurred."}), 500
        return render_template("base.html", error_title="500 - Server Error", error_message="An internal server error occurred."), 500

    return app

# Lazy WSGI application instance to resolve the 'app:app' import target if invoked
_app_instance = None

def __getattr__(name: str):
    global _app_instance
    if name == "app":
        if _app_instance is None:
            _app_instance = create_app()
        return _app_instance
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

