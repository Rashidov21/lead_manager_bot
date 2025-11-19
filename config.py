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

# Reminder Configuration (seconds)
REMINDER_CALL1_IMMEDIATE = 0
REMINDER_CALL1_1H = 3600
REMINDER_CALL1_3H = 10800
REMINDER_CALL1_12H = 43200
REMINDER_CALL2_DELAY = 7200  # 2 hours after Call #1 Done
REMINDER_CALL3_DELAY = 86400  # 24 hours after Call #2 Done
REMINDER_FOLLOWUP_MARGIN = 0  # send exactly at planned time
REMINDER_FIRST_CLASS_24H = 86400
REMINDER_FIRST_CLASS_2H = 7200

# Google Sheets Column Names (Uzbek headers)
COLUMNS = {
    "ROW_NUM": 0,  # Column "N" (optional)
    "ID": 1,
    "Name": 2,  # "Ism"
    "Phone": 3,  # "Raqam"
    "Seller": 4,  # "Sotuvchi"
    "Lead_Source": 5,  # "Manba"
    "Created_At": 6,  # "Sana"
    "Status": 7,
    "Call_1_Time": 8,  # "Call #1 Vaqti"
    "Call_2_Time": 9,  # "Call #2 Vaqti"
    "Call_3_Time": 10,  # "Call #3 Vaqti"
    "Next_Followup": 11,  # "Qayta aloqa"
    "First_Class_Date": 12,  # "1-dars kuni"
    "First_Class_Confirm": 13,  # "1-dars tasdig'i"
    "Comment": 14,  # "Izoh"
    "Last_Update": 15,  # "Oxirgi o'zgarish"
}

# Lead Status Values
STATUS_NEW_LEAD = "New Lead"
STATUS_CALL1_NEEDED = "Call #1 Needed"
STATUS_CALL1_DONE = "Call #1 Done"
STATUS_CALL2_NEEDED = "Call #2 Needed"
STATUS_CALL2_DONE = "Call #2 Done"
STATUS_CALL3_NEEDED = "Call #3 Needed"
STATUS_CALL3_DONE = "Call #3 Done"
STATUS_FOLLOWUP_NEEDED = "Follow-up Needed"
STATUS_FOLLOWUP_DONE = "Follow-up Done"
STATUS_FIRST_CLASS_SCHEDULED = "First Class Scheduled"
STATUS_FIRST_CLASS_CONFIRMED = "First Class Confirmed"
STATUS_NO_ANSWER = "No Answer"
STATUS_COLD_LEAD = "Cold Lead"
STATUS_LOST_LEAD = "Lost Lead"

VALID_STATUSES = [
    STATUS_NEW_LEAD,
    STATUS_CALL1_NEEDED,
    STATUS_CALL1_DONE,
    STATUS_CALL2_NEEDED,
    STATUS_CALL2_DONE,
    STATUS_CALL3_NEEDED,
    STATUS_CALL3_DONE,
    STATUS_FOLLOWUP_NEEDED,
    STATUS_FOLLOWUP_DONE,
    STATUS_FIRST_CLASS_SCHEDULED,
    STATUS_FIRST_CLASS_CONFIRMED,
    STATUS_NO_ANSWER,
    STATUS_COLD_LEAD,
    STATUS_LOST_LEAD,
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

