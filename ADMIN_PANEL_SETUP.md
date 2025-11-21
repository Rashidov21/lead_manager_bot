# Admin Panel Setup Guide

## Overview

The Lead Manager Admin Panel is a FastAPI-based web interface for managing sales agents, leads, KPI reports, and system monitoring.

## Installation

1. **Install Dependencies**

```bash
pip install -r requirements.txt
```

2. **Create First Admin User**

```bash
python admin_backend/create_admin.py
```

Follow the prompts to create your first admin account.

3. **Set JWT Secret Key (Optional but Recommended)**

Add to your `.env` file:
```
JWT_SECRET_KEY=your-very-secure-secret-key-here
```

## Running the Admin Panel

### Option 1: Using the run script
```bash
python admin_backend/run_admin.py
```

### Option 2: Using uvicorn directly
```bash
uvicorn admin_backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### Option 3: Running alongside the Telegram bot
The admin panel can run independently on port 8000 while the Telegram bot runs on its own process.

## Accessing the Admin Panel

- **URL**: http://localhost:8000
- **Login**: http://localhost:8000/admin/login
- **Default**: Use the credentials you created with `create_admin.py`

## Features

### 1. Dashboard
- Real-time statistics
- Charts (Leads by Source, Leads per Agent, 7-Day Activity)
- Conversion funnel
- Auto-refreshes every 30 seconds

### 2. Sales Agents Management
- View all agents
- Add new agents
- Edit agent information
- Delete/deactivate agents
- Reassign leads when deleting agents

### 3. Leads Management
- View all leads from Google Sheets
- Search by name, phone, or ID
- Filter by status, seller, source
- Sort by date, seller, or status
- View detailed lead information

### 4. KPI Reports
- View KPI metrics for each sales agent
- Export to CSV, Excel, or PDF
- Metrics include:
  - Call completion rates
  - Follow-up completion
  - First lesson scheduling
  - Attendance rates
  - Conversion percentages

### 5. System Logs
- Track all system actions
- Filter by action type, user type, or lead ID
- View detailed audit trail

### 6. Sync Status
- Monitor Google Sheet sync status
- View last sync time and row count
- Force manual sync
- View sync history

## API Endpoints

All API endpoints require authentication via JWT token (stored in cookie).

### Authentication
- `GET /admin/login` - Login page
- `POST /admin/login` - Authenticate user
- `GET /admin/logout` - Logout user

### Dashboard
- `GET /admin/dashboard` - Dashboard page
- `GET /admin/api/dashboard/stats` - Get dashboard statistics

### Agents
- `GET /admin/agents` - Agents management page
- `GET /admin/api/agents` - Get all agents
- `POST /admin/api/agents` - Create agent
- `PUT /admin/api/agents/{id}` - Update agent
- `DELETE /admin/api/agents/{id}` - Delete agent

### Leads
- `GET /admin/leads` - Leads management page
- `GET /admin/api/leads` - Get leads (with filters)
- `GET /admin/api/leads/{id}` - Get lead details
- `PUT /admin/api/leads/{id}` - Update lead

### KPI
- `GET /admin/kpi` - KPI reports page
- `GET /admin/api/kpi/sellers` - Get KPI for all sellers
- `GET /admin/api/kpi/export?format=csv|excel|pdf` - Export KPI

### Stats
- `GET /admin/api/stats/charts?period=week|month` - Get chart data

### Logs
- `GET /admin/logs` - System logs page
- `GET /admin/api/logs` - Get system logs (with filters)

### Sync
- `GET /admin/sync` - Sync status page
- `GET /admin/api/sync/status` - Get sync status
- `POST /admin/api/sync/force` - Force sync

## Security Notes

1. **Change JWT Secret Key**: Update `JWT_SECRET_KEY` in `.env` for production
2. **HTTPS**: Use HTTPS in production
3. **Password Strength**: Enforce strong passwords for admin users
4. **Session Timeout**: JWT tokens expire after 8 hours

## Troubleshooting

### Cannot login
- Verify admin user exists: Run `create_admin.py` again
- Check database: Ensure `admin_users` table exists
- Check JWT secret: Verify `JWT_SECRET_KEY` is set

### Charts not loading
- Check browser console for errors
- Verify Chart.js is loading (check network tab)
- Ensure API endpoints return data

### Sync not working
- Verify Google Sheets credentials
- Check `GOOGLE_SHEET_ID` and `GOOGLE_SHEET_NAME` in `.env`
- Ensure service account has access to the sheet

## Integration with Telegram Bot

The admin panel shares the same database and Google Sheets integration as the Telegram bot. Both can run simultaneously:

1. **Telegram Bot**: `python main.py` (runs on its own)
2. **Admin Panel**: `python admin_backend/run_admin.py` (runs on port 8000)

They share:
- SQLite database (`data/database.db`)
- Google Sheets client
- KPI service
- System logs

## Development

### File Structure
```
admin_backend/
├── __init__.py
├── main.py              # FastAPI app
├── auth.py              # JWT authentication
├── routes.py            # All API routes
├── stats_service.py     # Chart data service
├── export_service.py    # Export functionality
├── create_admin.py      # Admin user creation script
├── run_admin.py         # Run script
├── templates/           # Jinja2 templates
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── agents.html
│   ├── leads.html
│   ├── kpi.html
│   ├── logs.html
│   └── sync.html
└── static/              # Static files (CSS, JS, images)
```

### Adding New Features

1. Add route in `routes.py`
2. Create template in `templates/`
3. Add service function if needed
4. Update navigation in `base.html`

## Support

For issues or questions, check:
- Database logs: `data/bot.log`
- FastAPI logs: Console output
- Browser console: For frontend errors

