# Lead Manager Bot

A Telegram bot that works as a CRM automation and reminder system integrated with Google Sheets. The bot automatically tracks lead status, sends reminders, and provides KPI analytics to admins.

## Features

- **Google Sheets Integration**: Real-time reading and updating of lead data
- **Automated Reminders**: 
  - Call #1 reminders (1h, 2h, 12h escalation)
  - Call #2 and #3 automatic scheduling
  - First class reminders (24h and 2h before)
  - Follow-up notifications
- **Role-Based Access**: Separate commands for sellers and admins
- **KPI Analytics**: Comprehensive statistics and performance metrics
- **24/7 Operation**: Fully automated with persistent scheduler

## Tech Stack

- Python 3.10+
- Aiogram 3.x (async Telegram bot framework)
- APScheduler (background tasks)
- gspread (Google Sheets API)
- SQLite (user roles and state)
- Loguru (logging)

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd lead_manager_bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Google Service Account**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable Google Sheets API and Google Drive API
   - Create a Service Account
   - Download the JSON key file
   - Place it in `data/service_account.json`
   - Share your Google Sheet with the service account email

4. **Configure environment variables**
   Create a `.env` file in the project root:
   ```env
   BOT_TOKEN=your_telegram_bot_token
   GOOGLE_SHEET_ID=your_google_sheet_id
   GOOGLE_SHEET_NAME=Sheet1
   ADMIN_IDS=123456789,987654321
   SHEET_POLL_INTERVAL=120
   LOG_LEVEL=INFO
   ```

5. **Set up Google Sheet**
   Your Google Sheet must have the following columns (in order):
   - ID
   - Name
   - Phone
   - Seller
   - Lead Source
   - Created_At
   - Status
   - Call_1_Time
   - Call_2_Time
   - Call_3_Time
   - Next_Followup
   - First_Class_Date
   - First_Class_Confirm
   - Comment
   - Last_Update

6. **Initialize database**
   The database will be created automatically on first run.

## Usage

1. **Start the bot**
   ```bash
   python main.py
   ```

2. **Add users**
   - Users are automatically added when they use `/start`
   - To make a user an admin, update the database or use the `ADMIN_IDS` environment variable

3. **Seller Commands**
   - `/start` - Start the bot
   - `/mylids` - View your leads
   - `/pending` - View pending tasks
   - `/update_status` - Update lead status
   - `/help` - Show help

4. **Admin Commands**
   - `/dashboard` - View dashboard with key metrics
   - `/allstats` - View all statistics
   - `/sellerstats` - View seller performance
   - `/lazy` - View sellers with overdue tasks
   - `/settings` - Bot settings

## Workflow

1. Salesperson adds a lead to Google Sheets
2. Bot detects the new lead (polls every 1-3 minutes)
3. Bot sends reminders based on status and time:
   - Call #1: 1h, 2h reminders, 12h escalation to admin
   - Call #2: Automatically scheduled 2h after Call #1
   - Call #3: Automatically scheduled 24h after Call #2
   - First Class: 24h and 2h before reminders
4. Seller updates status via bot
5. Bot writes updates back to Google Sheets
6. Admin receives daily/weekly KPI summaries

## Project Structure

```
project/
│── bot.py                 # Main bot class
│── config.py              # Configuration
│── main.py                # Entry point
│── requirements.txt       # Dependencies
│── google_sheets.py       # Google Sheets integration
│── scheduler.py           # Background scheduler
│── database.py            # Database operations
│── handlers/
│     ├── admin.py         # Admin handlers
│     ├── seller.py        # Seller handlers
│     ├── common.py        # Common handlers
│── services/
│     ├── reminders.py     # Reminder logic
│     ├── kpi.py           # KPI analytics
│── utils/
│     ├── time_utils.py    # Time utilities
│     ├── validation.py    # Validation utilities
│── data/
│     ├── service_account.json  # Google service account
│     ├── database.db      # SQLite database
│     └── bot.log          # Log file
```

## Configuration

### Reminder Timings

Default reminder timings (can be modified in `config.py`):
- Call #1 Reminder 1: 1 hour
- Call #1 Reminder 2: 2 hours
- Call #1 Escalation: 12 hours
- Call #2 Delay: 2 hours after Call #1
- Call #3 Delay: 24 hours after Call #2
- First Class Reminder 1: 24 hours before
- First Class Reminder 2: 2 hours before

### Polling Frequency

Default: 120 seconds (2 minutes). Can be changed via `SHEET_POLL_INTERVAL` environment variable.

## Error Handling

- Automatic retry for Google Sheets operations (3 attempts with exponential backoff)
- Graceful error handling for all bot operations
- Comprehensive logging with Loguru
- Duplicate reminder prevention

## Performance

- Supports thousands of leads
- Efficient polling with configurable intervals
- Persistent scheduler state
- Async/await throughout for optimal performance

## License

[Your License Here]

## Support

For issues and questions, please open an issue on GitHub.

