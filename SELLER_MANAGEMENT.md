# Seller Management System

## Overview

The Lead Manager Bot includes a comprehensive seller management system with:
- Database storage for sellers
- Telegram bot integration
- Web admin panel for statistics
- Automatic notifications for new leads and status changes

## Workflow

### 1. Admin Adds Seller

**Via Telegram Bot:**
```
/add_seller Ahmad
/add_seller Ahmad 1234567890
/add_seller Ahmad va 1234567890
```

**Via Web Admin Panel:**
- Navigate to http://localhost:5000
- Use the API endpoint: `POST /api/seller/add`
- Or use the web interface (if implemented)

**What happens:**
1. Seller is added to `sellers` table in database
2. Bot checks Google Sheets for existing leads with this seller name
3. If Telegram ID provided, seller is automatically linked
4. Admin receives confirmation with lead count

### 2. Seller Links to Telegram

**Via Telegram Bot:**
```
/link_seller Ahmad
/link_seller Ahmad va 1234567890
```

**What happens:**
1. Bot validates seller exists in database
2. Links Telegram account to seller record
3. Verifies link and shows lead count
4. Seller can now use all bot commands

### 3. Lead Monitoring & Notifications

**Automatic Process:**
- Bot polls Google Sheets every 1-3 minutes (configurable)
- Detects new leads assigned to sellers
- Detects status changes in existing leads
- Sends notifications to linked sellers

**New Lead Notification:**
- Seller receives: "🆕 Yangi Lid Qo'shildi!"
- Includes: Lead ID, Name, Phone, Source, Status
- Auto-updates status to "Call #1 Needed" if needed
- Sets Call #1 time automatically

**Status Change Notification:**
- Seller receives: "🔄 Lid Holati O'zgardi"
- Only for significant changes (Call #1/2/3 Done, First Class, Follow-up)
- Includes old and new status
- Provides context about next steps

## Database Structure

### Sellers Table
```sql
CREATE TABLE sellers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_name TEXT NOT NULL UNIQUE,
    telegram_id INTEGER,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
```

## Google Sheets Integration

### Seller Matching
- Bot matches sellers by the "Sotuvchi" column in Google Sheets
- Matching is case-insensitive
- Trims whitespace for reliable matching
- Seller name in sheet must match seller_name in database

### Lead Assignment
- When a lead is added to Google Sheets with a seller name
- Bot detects it and notifies the seller
- If seller not linked, lead is still tracked but no notification sent

## Web Admin Panel

### Access
- URL: http://localhost:5000
- Run: `python web_admin/run_web.py`

### Features
- View all sellers with statistics
- See lead counts per seller
- View conversion rates
- Check which sellers are linked to Telegram
- Add/link sellers via API

### API Endpoints

**Get All Sellers:**
```
GET /api/sellers
```

**Get Seller Details:**
```
GET /api/seller/<seller_name>
```

**Add Seller:**
```
POST /api/seller/add
Body: {"name": "Ahmad", "telegram_id": 1234567890}
```

**Link Seller:**
```
POST /api/seller/link
Body: {"name": "Ahmad", "telegram_id": 1234567890}
```

**Get Overview:**
```
GET /api/overview
```

## Commands Reference

### Admin Commands
- `/add_seller <name> [telegram_id]` - Add seller to database
- `/add_seller <name> va <telegram_id>` - Add seller with Telegram ID
- `/link_seller <name> va <telegram_id>` - Link existing seller to Telegram

### Seller Commands
- `/link_seller <name>` - Link yourself to a seller record
- `/myleads` - View your assigned leads
- `/pending` - View pending tasks
- `/update_status` - Update lead status
- `/followup` - Schedule follow-up
- `/kpi` - View personal KPI

## Monitoring Service

The `LeadMonitorService` runs automatically via scheduler:
- Checks for new leads every polling interval
- Checks for status changes every polling interval
- Sends notifications to sellers
- Updates lead state in database

## Best Practices

1. **Seller Names:**
   - Use consistent naming in Google Sheets
   - Match exactly with database (case-insensitive)
   - Avoid special characters that might cause issues

2. **Adding Sellers:**
   - Add seller to database first via `/add_seller`
   - Then add leads to Google Sheets with seller name
   - Or link seller to Telegram if they already have leads

3. **Linking:**
   - Sellers can link themselves via `/link_seller`
   - Admins can link via `/add_seller` with Telegram ID
   - Or use web admin panel API

4. **Notifications:**
   - Ensure sellers are linked before adding leads
   - Bot will notify automatically when leads are added
   - Status changes trigger notifications automatically

