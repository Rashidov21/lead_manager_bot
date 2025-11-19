"""
Database module for SQLite operations.
Manages user roles, reminder state, and bot internal data.
"""
import aiosqlite
from typing import Optional, List, Dict
from loguru import logger

from config import DATABASE_PATH


async def init_database():
    """Initialize database with required tables."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Users table (Telegram users with roles)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                role TEXT NOT NULL DEFAULT 'seller',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Reminders table (tracks sent reminders to prevent duplicates)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id TEXT NOT NULL,
                reminder_type TEXT NOT NULL,
                scheduled_time TEXT NOT NULL,
                sent_time TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                UNIQUE(lead_id, reminder_type, scheduled_time)
            )
        """)

        # Lead state table (tracks last known state of leads)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS lead_state (
                lead_id TEXT PRIMARY KEY,
                last_status TEXT,
                last_updated TEXT NOT NULL,
                last_checked TEXT NOT NULL
            )
        """)

        # Scheduler jobs table (for persistent scheduler state)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS scheduler_jobs (
                job_id TEXT PRIMARY KEY,
                job_type TEXT NOT NULL,
                lead_id TEXT,
                scheduled_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL
            )
        """)

        await db.commit()
        logger.info("Database initialized successfully")


async def get_user_role(telegram_id: int) -> Optional[str]:
    """Get user role by Telegram ID."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT role FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row["role"] if row else None


async def is_admin(telegram_id: int) -> bool:
    """Check if user is admin."""
    role = await get_user_role(telegram_id)
    return role == "admin"


async def is_seller(telegram_id: int) -> bool:
    """Check if user is seller."""
    role = await get_user_role(telegram_id)
    return role in ("seller", "admin")  # Admins can also use seller commands


async def add_user(telegram_id: int, username: Optional[str], full_name: Optional[str], role: str = "seller"):
    """Add or update user in database."""
    from utils.time_utils import now_utc, format_datetime

    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO users (telegram_id, username, full_name, role, created_at, updated_at)
            VALUES (?, ?, ?, ?, 
                COALESCE((SELECT created_at FROM users WHERE telegram_id = ?), ?),
                ?)
        """, (telegram_id, username, full_name, role, telegram_id, format_datetime(now_utc()), format_datetime(now_utc())))
        await db.commit()
        logger.info(f"User {telegram_id} added/updated with role {role}")


async def get_all_sellers() -> List[Dict]:
    """Get all sellers from database."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE role = 'seller' OR role = 'admin'") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_all_admins() -> List[Dict]:
    """Get all admins from database."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE role = 'admin'") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def mark_reminder_sent(lead_id: str, reminder_type: str, scheduled_time: str) -> bool:
    """Mark a reminder as sent to prevent duplicates."""
    from utils.time_utils import now_utc, format_datetime

    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            await db.execute("""
                INSERT INTO reminders (lead_id, reminder_type, scheduled_time, sent_time, status, created_at)
                VALUES (?, ?, ?, ?, 'sent', ?)
            """, (lead_id, reminder_type, scheduled_time, format_datetime(now_utc()), format_datetime(now_utc())))
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            # Reminder already exists
            return False


async def was_reminder_sent(lead_id: str, reminder_type: str, scheduled_time: str) -> bool:
    """Check if a reminder was already sent."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("""
            SELECT COUNT(*) as count FROM reminders
            WHERE lead_id = ? AND reminder_type = ? AND scheduled_time = ? AND status = 'sent'
        """, (lead_id, reminder_type, scheduled_time)) as cursor:
            row = await cursor.fetchone()
            return row[0] > 0 if row else False


async def update_lead_state(lead_id: str, status: str):
    """Update last known state of a lead."""
    from utils.time_utils import now_utc, format_datetime

    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO lead_state (lead_id, last_status, last_updated, last_checked)
            VALUES (?, ?, ?, ?)
        """, (lead_id, status, format_datetime(now_utc()), format_datetime(now_utc())))
        await db.commit()


async def get_lead_state(lead_id: str) -> Optional[Dict]:
    """Get last known state of a lead."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM lead_state WHERE lead_id = ?", (lead_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def save_scheduler_job(job_id: str, job_type: str, lead_id: Optional[str], scheduled_time: str):
    """Save scheduler job to database for persistence."""
    from utils.time_utils import format_datetime, now_utc

    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO scheduler_jobs (job_id, job_type, lead_id, scheduled_time, status, created_at)
            VALUES (?, ?, ?, ?, 'pending', ?)
        """, (job_id, job_type, lead_id, scheduled_time, format_datetime(now_utc())))
        await db.commit()


async def mark_job_completed(job_id: str):
    """Mark scheduler job as completed."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("UPDATE scheduler_jobs SET status = 'completed' WHERE job_id = ?", (job_id,))
        await db.commit()

