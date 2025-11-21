"""
Run the FastAPI Admin Panel.
Usage: python admin_backend/run_admin.py
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import uvicorn

if __name__ == "__main__":
    print("=" * 50)
    print("Starting Lead Manager Admin Panel")
    print("=" * 50)
    print("Access at: http://localhost:8000")
    print("Login at: http://localhost:8000/admin/login")
    print("=" * 50)
    
    uvicorn.run(
        "admin_backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

