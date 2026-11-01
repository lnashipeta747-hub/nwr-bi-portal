"""
run.py
-------
Entry point. `python3 run.py` starts the Flask development server.

For a live demo/presentation:
    export FLASK_ENV=development
    python3 run.py
Then open http://localhost:5000
"""

import os
from app import create_app

app = create_app(os.environ.get("FLASK_ENV", "development"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=app.config.get("DEBUG", False), use_reloader=False)
