"""
Script to create the first admin user for the web panel.
Usage: python admin_backend/create_admin.py
"""
import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from admin_backend.auth import get_password_hash
from database import create_admin_user, init_database


async def main():
    """Create admin user."""
    await init_database()
    
    print("=" * 50)
    print("Create Admin User for Web Panel")
    print("=" * 50)
    
    email = input("Enter admin email: ").strip()
    if not email:
        print("Error: Email is required")
        return
    
    password = input("Enter admin password: ").strip()
    if not password or len(password) < 6:
        print("Error: Password must be at least 6 characters")
        return
    
    full_name = input("Enter admin full name (optional): ").strip() or None
    
    password_hash = get_password_hash(password)
    
    success = await create_admin_user(email, password_hash, full_name)
    
    if success:
        print(f"\n✅ Admin user '{email}' created successfully!")
        print("You can now login to the admin panel at http://localhost:8000/admin/login")
    else:
        print(f"\n⚠️  Admin user '{email}' already exists.")


if __name__ == "__main__":
    asyncio.run(main())

