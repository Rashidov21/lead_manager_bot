"""
Configuration management for the Lead Manager Bot.
Uses environment variables for sensitive data.
"""
import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Telegram Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")

# Google Sheets Configuration
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "Лист1")
SERVICE_ACCOUNT_PATH = DATA_DIR / "service_account.json"

if not GOOGLE_SHEET_ID:
    raise ValueError("GOOGLE_SHEET_ID environment variable is required")

if not SERVICE_ACCOUNT_PATH.exists():
    raise FileNotFoundError(
        f"Service account file not found at {SERVICE_ACCOUNT_PATH}. "
        "Please add your Google Service Account JSON file."
    )

# Database Configuration
DATABASE_PATH = DATA_DIR / "database.db"

# Polling Configuration
SHEET_POLL_INTERVAL = int(os.getenv("SHEET_POLL_INTERVAL", 120))  # seconds (2 minutes default)

# Reminder Configuration
REMINDER_CALL1_1H = 3600  # 1 hour in seconds
REMINDER_CALL1_2H = 7200  # 2 hours in seconds
REMINDER_CALL1_12H = 43200  # 12 hours in seconds
REMINDER_CALL2_DELAY = 7200  # 2 hours after Call #1 Done
REMINDER_CALL3_DELAY = 86400  # 24 hours after Call #2 Done
REMINDER_FIRST_CLASS_24H = 86400  # 24 hours before first class
REMINDER_FIRST_CLASS_2H = 7200  # 2 hours before first class

# Google Sheets Column Names
COLUMNS = {
    "ID": 0,
    "Name": 1,
    "Phone": 2,
    "Seller": 3,
    "Lead_Source": 4,
    "Created_At": 5,
    "Status": 6,
    "Call_1_Time": 7,
    "Call_2_Time": 8,
    "Call_3_Time": 9,
    "Next_Followup": 10,
    "First_Class_Date": 11,
    "First_Class_Confirm": 12,
    "Comment": 13,
    "Last_Update": 14,
}

# Lead Status Values
STATUS_CALL1_NEEDED = "Call #1 Needed"
STATUS_CALL1_DONE = "Call #1 Done"
STATUS_CALL2_DONE = "Call #2 Done"
STATUS_CALL3_DONE = "Call #3 Done"
STATUS_FIRST_CLASS_PENDING = "First Class Pending Confirmation"
STATUS_DID_NOT_ATTEND = "Did Not Attend First Class"
STATUS_COMPLETED = "Completed"
STATUS_LOST = "Lost"

VALID_STATUSES = [
    STATUS_CALL1_NEEDED,
    STATUS_CALL1_DONE,
    STATUS_CALL2_DONE,
    STATUS_CALL3_DONE,
    STATUS_FIRST_CLASS_PENDING,
    STATUS_DID_NOT_ATTEND,
    STATUS_COMPLETED,
    STATUS_LOST,
]

# User Roles
ROLE_SELLER = "seller"
ROLE_ADMIN = "admin"

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = DATA_DIR / "bot.log"

# Retry Configuration
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# Admin Telegram IDs (comma-separated)
ADMIN_IDS: List[int] = [
    int(admin_id.strip())
    for admin_id in os.getenv("ADMIN_IDS", "").split(",")
    if admin_id.strip().isdigit()
]

