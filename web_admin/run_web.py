"""
Run the web admin panel separately.
Usage: python web_admin/run_web.py
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from web_admin.app import app

if __name__ == '__main__':
    print("Starting Lead Manager Web Admin Panel...")
    print("Access at: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)

