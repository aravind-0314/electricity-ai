"""
WSGI entry point for Gunicorn / Render production deployment.
Eliminates the module/package naming conflict between app.py and app/ package directory.
"""
import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from config import Config

# WSGI application callable for Gunicorn
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", Config.PORT))
    host = os.environ.get("HOST", Config.HOST)
    debug = os.environ.get("FLASK_DEBUG", "1" if Config.DEBUG else "0") == "1"
    print("=" * 60)
    print(f" {Config.PROJECT_NAME} - {Config.PROJECT_SUBTITLE}")
    print(f" Starting on http://{host}:{port}")
    print("=" * 60)
    app.run(host=host, port=port, debug=debug)

