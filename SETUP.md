# Setup Guide

## Prerequisites

- Python 3.10 or higher
- A Telegram Bot Token (get from [@BotFather](https://t.me/BotFather))
- A Google Cloud Project with Sheets API enabled
- A Google Service Account JSON key file

## Step-by-Step Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the instructions
3. Copy the bot token you receive

### 3. Set Up Google Sheets API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the following APIs:
   - Google Sheets API
   - Google Drive API
4. Create a Service Account:
   - Go to "IAM & Admin" > "Service Accounts"
   - Click "Create Service Account"
   - Give it a name (e.g., "lead-manager-bot")
   - Grant it "Editor" role (or create a custom role with Sheets read/write permissions)
   - Click "Done"
5. Create a key for the service account:
   - Click on the service account you just created
   - Go to "Keys" tab
   - Click "Add Key" > "Create new key"
   - Choose JSON format
   - Download the JSON file
6. Save the JSON file as `data/service_account.json`

### 4. Create Google Sheet

1. Create a new Google Sheet
2. Set up the header row with these exact column names (in order):
   ```
   ID | Name | Phone | Seller | Lead Source | Created_At | Status | Call_1_Time | Call_2_Time | Call_3_Time | Next_Followup | First_Class_Date | First_Class_Confirm | Comment | Last_Update
   ```
3. Share the sheet with the service account email (found in the JSON file, looks like `xxx@xxx.iam.gserviceaccount.com`)
   - Give it "Editor" permissions
4. Copy the Sheet ID from the URL:
   - URL format: `https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit`
   - The SHEET_ID_HERE is what you need
 
### 5. Configure Environment Variables

Create a `.env` file in the project root:

```env
BOT_TOKEN=your_telegram_bot_token_here
GOOGLE_SHEET_ID=your_google_sheet_id_here
GOOGLE_SHEET_NAME=Sheet1
ADMIN_IDS=123456789,987654321
SHEET_POLL_INTERVAL=120
LOG_LEVEL=INFO
```

**Important:**
- Replace `your_telegram_bot_token_here` with your actual bot token
- Replace `your_google_sheet_id_here` with your actual sheet ID
- Replace `123456789,987654321` with your Telegram user IDs (comma-separated)
  - To find your Telegram ID, message [@userinfobot](https://t.me/userinfobot) on Telegram

### 6. Initialize Database

The database will be created automatically on first run. No manual setup needed.

### 7. Run the Bot

```bash
python main.py
```

The bot will:
- Initialize the database
- Connect to Google Sheets
- Start the scheduler
- Begin polling for Telegram messages

## Testing

1. Start the bot
2. Open Telegram and search for your bot
3. Send `/start` to register yourself
4. If you're an admin (your ID is in ADMIN_IDS), you'll see admin commands
5. Add a test lead to your Google Sheet
6. Wait 1-3 minutes for the bot to detect it
7. Check if reminders are sent correctly

## Troubleshooting

### Bot doesn't respond
- Check if BOT_TOKEN is correct
- Verify the bot is running (check logs in `data/bot.log`)

### Google Sheets errors
- Verify `data/service_account.json` exists and is valid
- Check that the sheet is shared with the service account email
- Verify GOOGLE_SHEET_ID is correct
- Check that column names match exactly

### Reminders not sending
- Check logs in `data/bot.log`
- Verify seller names in the sheet match Telegram usernames/full names
- Check that users have used `/start` to register

### Database errors
- Ensure the `data/` directory exists and is writable
- Check file permissions

## Seller Name Matching

The bot matches sellers by:
1. Full name (from Telegram profile)
2. Username (from Telegram)

Make sure the "Seller" column in your Google Sheet matches one of these values.

## Admin Setup

To make a user an admin:
1. Add their Telegram ID to the `ADMIN_IDS` environment variable
2. Or update the database directly:
   ```sql
   UPDATE users SET role = 'admin' WHERE telegram_id = YOUR_TELEGRAM_ID;
   ```

## Production Deployment

For production:
1. Use a process manager like `systemd`, `supervisord`, or `pm2`
2. Set up log rotation
3. Use environment variables (never commit `.env` file)
4. Set up monitoring and alerts
5. Consider using a database backup solution

Example systemd service file (`/etc/systemd/system/lead-manager-bot.service`):

```ini
[Unit]
Description=Lead Manager Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/lead_manager_bot
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable lead-manager-bot
sudo systemctl start lead-manager-bot
```

