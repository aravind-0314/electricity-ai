"""
Entry point for Electricity Theft & Distribution Loss Detection Web Application.
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

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", Config.PORT))
    host = os.environ.get("HOST", Config.HOST)
    debug = os.environ.get("FLASK_DEBUG", "1" if Config.DEBUG else "0") == "1"

    print("=" * 60)
    print(f" {Config.PROJECT_NAME} - {Config.PROJECT_SUBTITLE}")
    print(f" Institution: {Config.COLLEGE}")
    print(f" Department:  {Config.DEPARTMENT}")
    print(f" Guide:       {Config.PROJECT_GUIDE}")
    print(f" Starting on http://{host}:{port}")
    print("=" * 60)
    app.run(host=host, port=port, debug=debug)

