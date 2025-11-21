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

        # Sellers table (managed by admins)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sellers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_name TEXT NOT NULL UNIQUE,
                telegram_id INTEGER,
                is_active INTEGER NOT NULL DEFAULT 1,
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

        # Admin users table (for web admin panel authentication)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_login TEXT
            )
        """)

        # System logs table (for tracking all actions)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_type TEXT NOT NULL,
                user_id TEXT,
                user_name TEXT,
                action_type TEXT NOT NULL,
                lead_id TEXT,
                old_value TEXT,
                new_value TEXT,
                details TEXT
            )
        """)

        # Google Sheet sync status table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sync_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sync_time TEXT NOT NULL,
                status TEXT NOT NULL,
                rows_count INTEGER,
                new_leads_count INTEGER,
                error_message TEXT
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
    """Check if user is admin - checks both database role and ADMIN_IDS from config."""
    from config import ADMIN_IDS
    
    # First check if user is in ADMIN_IDS from environment
    if telegram_id in ADMIN_IDS:
        return True
    
    # Then check database role
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
    """Get all sellers from sellers table."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM sellers WHERE is_active = 1") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_seller_by_name(seller_name: str) -> Optional[Dict]:
    """Get seller by name (case-insensitive, trimmed)."""
    if not seller_name or not seller_name.strip():
        return None
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM sellers WHERE LOWER(TRIM(seller_name)) = LOWER(TRIM(?))", 
            (seller_name.strip(),)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_seller_by_telegram(telegram_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM sellers WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def add_seller_record(seller_name: str, telegram_id: Optional[int] = None, is_active: bool = True):
    """Create or reactivate a seller."""
    from utils.time_utils import now_utc, format_datetime

    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            INSERT INTO sellers (seller_name, telegram_id, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(seller_name) DO UPDATE SET
                telegram_id=excluded.telegram_id,
                is_active=excluded.is_active,
                updated_at=excluded.updated_at
            """,
            (
                seller_name.strip(),
                telegram_id,
                1 if is_active else 0,
                format_datetime(now_utc()),
                format_datetime(now_utc()),
            ),
        )
        await db.commit()


async def link_seller_to_telegram(seller_name: str, telegram_id: int) -> bool:
    """Attach a Telegram user to an existing seller. Returns True if successful."""
    from utils.time_utils import now_utc, format_datetime

    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """
            UPDATE sellers
            SET telegram_id = ?, updated_at = ?, is_active = 1
            WHERE LOWER(seller_name) = LOWER(?)
            """,
            (telegram_id, format_datetime(now_utc()), seller_name.strip()),
        )
        await db.commit()
        return cursor.rowcount > 0


async def deactivate_seller(seller_name: str):
    """Soft-deactivate seller."""
    from utils.time_utils import now_utc, format_datetime

    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            UPDATE sellers SET is_active = 0, updated_at = ?
            WHERE LOWER(seller_name) = LOWER(?)
            """,
            (format_datetime(now_utc()), seller_name),
        )
        await db.commit()


async def get_all_admins() -> List[Dict]:
    """Get all admins from database and include ADMIN_IDS from config."""
    from config import ADMIN_IDS
    from utils.time_utils import now_utc, format_datetime
    
    admins = []
    admin_ids_seen = set()
    
    # Get admins from database
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE role = 'admin'") as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                admin_dict = dict(row)
                admins.append(admin_dict)
                admin_ids_seen.add(admin_dict["telegram_id"])
    
    # Add admins from ADMIN_IDS config that aren't in database
    for admin_id in ADMIN_IDS:
        if admin_id not in admin_ids_seen:
            # Create a minimal admin dict for env admins
            admins.append({
                "telegram_id": admin_id,
                "username": None,
                "full_name": None,
                "role": "admin",
                "created_at": format_datetime(now_utc()),
                "updated_at": format_datetime(now_utc())
            })
    
    return admins


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


# Admin authentication functions
async def create_admin_user(email: str, password_hash: str, full_name: Optional[str] = None) -> bool:
    """Create a new admin user for web panel."""
    from utils.time_utils import now_utc, format_datetime
    
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute("""
                INSERT INTO admin_users (email, password_hash, full_name, is_active, created_at, updated_at)
                VALUES (?, ?, ?, 1, ?, ?)
            """, (email.lower(), password_hash, full_name, format_datetime(now_utc()), format_datetime(now_utc())))
            await db.commit()
            logger.info(f"Admin user created: {email}")
            return True
    except aiosqlite.IntegrityError:
        logger.warning(f"Admin user already exists: {email}")
        return False


async def get_admin_user(email: str) -> Optional[Dict]:
    """Get admin user by email."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM admin_users WHERE email = ? AND is_active = 1", (email.lower(),)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def update_admin_last_login(email: str):
    """Update last login time for admin user."""
    from utils.time_utils import now_utc, format_datetime
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE admin_users SET last_login = ? WHERE email = ?",
            (format_datetime(now_utc()), email.lower())
        )
        await db.commit()


# System logging functions
async def log_action(
    user_type: str,
    user_id: Optional[str],
    user_name: Optional[str],
    action_type: str,
    lead_id: Optional[str] = None,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
    details: Optional[str] = None
):
    """Log a system action."""
    from utils.time_utils import now_utc, format_datetime
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO system_logs 
            (timestamp, user_type, user_id, user_name, action_type, lead_id, old_value, new_value, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            format_datetime(now_utc()),
            user_type,
            user_id,
            user_name,
            action_type,
            lead_id,
            old_value,
            new_value,
            details
        ))
        await db.commit()


async def get_system_logs(
    limit: int = 100,
    offset: int = 0,
    action_type: Optional[str] = None,
    user_type: Optional[str] = None,
    lead_id: Optional[str] = None
) -> List[Dict]:
    """Get system logs with optional filters."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        query = "SELECT * FROM system_logs WHERE 1=1"
        params = []
        
        if action_type:
            query += " AND action_type = ?"
            params.append(action_type)
        
        if user_type:
            query += " AND user_type = ?"
            params.append(user_type)
        
        if lead_id:
            query += " AND lead_id = ?"
            params.append(lead_id)
        
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


# Sync status functions
async def save_sync_status(
    status: str,
    rows_count: Optional[int] = None,
    new_leads_count: Optional[int] = None,
    error_message: Optional[str] = None
):
    """Save Google Sheet sync status."""
    from utils.time_utils import now_utc, format_datetime
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO sync_status (sync_time, status, rows_count, new_leads_count, error_message)
            VALUES (?, ?, ?, ?, ?)
        """, (format_datetime(now_utc()), status, rows_count, new_leads_count, error_message))
        await db.commit()


async def get_latest_sync_status() -> Optional[Dict]:
    """Get the latest sync status."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM sync_status ORDER BY sync_time DESC LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

