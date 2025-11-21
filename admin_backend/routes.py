"""
FastAPI Routes for Admin Panel.
"""
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import asyncio

from admin_backend import auth
from database import (
    get_all_sellers,
    get_seller_by_name,
    add_seller_record,
    link_seller_to_telegram,
    deactivate_seller,
    log_action,
    get_system_logs,
    save_sync_status,
    get_latest_sync_status,
    create_admin_user,
    get_admin_user,
)
from google_sheets import sheets_client
from services.kpi import KPIService
from config import ADMIN_IDS, VALID_STATUSES

templates = Jinja2Templates(directory="admin_backend/templates")

# Routers
auth_router = APIRouter()
dashboard_router = APIRouter()
agents_router = APIRouter()
leads_router = APIRouter()
kpi_router = APIRouter()
stats_router = APIRouter()
logs_router = APIRouter()
sync_router = APIRouter()


# ========== AUTH ROUTES ==========

@auth_router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page."""
    return templates.TemplateResponse("login.html", {"request": request})


@auth_router.post("/login")
async def login(
    email: str = Form(...),
    password: str = Form(...),
    request: Request = None
):
    """Authenticate admin user."""
    user = await auth.authenticate_admin(email, password)
    if not user:
        if request:
            return templates.TemplateResponse(
                "login.html",
                {"request": request, "error": "Invalid email or password"}
            )
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = auth.create_access_token(data={"sub": user["email"]})
    
    response = RedirectResponse(url="/admin/dashboard", status_code=303)
    response.set_cookie(key="access_token", value=access_token, httponly=True, max_age=28800)
    return response


@auth_router.get("/logout")
async def logout():
    """Logout admin user."""
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie(key="access_token")
    return response


# ========== DASHBOARD ROUTES ==========

@dashboard_router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, current_admin: dict = Depends(auth.get_current_admin)):
    """Dashboard page."""
    return templates.TemplateResponse("dashboard.html", {"request": request, "admin": current_admin})


@dashboard_router.get("/api/dashboard/stats")
async def dashboard_stats(current_admin: dict = Depends(auth.get_current_admin)):
    """Get dashboard statistics."""
    try:
        kpi_service = KPIService()
        all_stats = await kpi_service.get_all_stats()
        seller_stats = await kpi_service.get_seller_stats()
        dashboard = await kpi_service.get_dashboard()
        
        # Get all leads
        all_leads = await sheets_client.get_all_leads()
        
        # Calculate today's stats
        from utils.time_utils import now_utc, parse_datetime
        today = now_utc().date()
        
        new_leads_today = sum(
            1 for lead in all_leads
            if lead.get("Created_At") and parse_datetime(lead["Created_At"]).date() == today
        )
        
        calls_today = sum(
            1 for lead in all_leads
            if (lead.get("Call_1_Time") and parse_datetime(lead["Call_1_Time"]).date() == today) or
               (lead.get("Call_2_Time") and parse_datetime(lead["Call_2_Time"]).date() == today) or
               (lead.get("Call_3_Time") and parse_datetime(lead["Call_3_Time"]).date() == today)
        )
        
        first_class_scheduled = sum(
            1 for lead in all_leads
            if lead.get("Status") == "First Class Scheduled"
        )
        
        first_class_confirmed = sum(
            1 for lead in all_leads
            if lead.get("Status") == "First Class Confirmed"
        )
        
        return JSONResponse({
            "total_leads": len(all_leads),
            "new_leads_today": new_leads_today,
            "calls_today": calls_today,
            "first_class_scheduled": first_class_scheduled,
            "first_class_confirmed": first_class_confirmed,
            "dashboard": dashboard,
            "seller_stats": seller_stats,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== AGENTS ROUTES ==========

@agents_router.get("/agents", response_class=HTMLResponse)
async def agents_page(request: Request, current_admin: dict = Depends(auth.get_current_admin)):
    """Sales agents management page."""
    return templates.TemplateResponse("agents.html", {"request": request, "admin": current_admin})


@agents_router.get("/api/agents")
async def get_agents(current_admin: dict = Depends(auth.get_current_admin)):
    """Get all sales agents."""
    try:
        sellers = await get_all_sellers()
        kpi_service = KPIService()
        stats = await kpi_service.get_seller_stats()
        
        agents_data = []
        for seller in sellers:
            seller_name = seller.get("seller_name", "")
            seller_stats = stats.get(seller_name, {})
            leads = await sheets_client.get_leads_by_seller(seller_name)
            
            agents_data.append({
                "id": seller.get("id"),
                "name": seller_name,
                "telegram_id": seller.get("telegram_id"),
                "is_active": bool(seller.get("is_active")),
                "is_linked": seller.get("telegram_id") is not None,
                "total_leads": len(leads),
                "stats": seller_stats,
                "created_at": seller.get("created_at"),
            })
        
        return JSONResponse({"agents": agents_data})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@agents_router.post("/api/agents")
async def create_agent(
    name: str = Form(...),
    telegram_id: Optional[int] = Form(None),
    phone: Optional[str] = Form(None),
    current_admin: dict = Depends(auth.get_current_admin)
):
    """Create a new sales agent."""
    try:
        # Check if agent already exists
        existing = await get_seller_by_name(name)
        if existing:
            raise HTTPException(status_code=400, detail=f"Agent '{name}' already exists")
        
        await add_seller_record(name, telegram_id=telegram_id, is_active=True)
        
        await log_action(
            user_type="admin",
            user_id=str(current_admin["id"]),
            user_name=current_admin.get("full_name") or current_admin["email"],
            action_type="agent_added",
            details=f"Added agent: {name}"
        )
        
        return JSONResponse({"success": True, "message": f"Agent '{name}' created successfully"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@agents_router.put("/api/agents/{agent_id}")
async def update_agent(
    agent_id: int,
    name: Optional[str] = Form(None),
    telegram_id: Optional[int] = Form(None),
    is_active: Optional[bool] = Form(None),
    current_admin: dict = Depends(auth.get_current_admin)
):
    """Update a sales agent."""
    try:
        # Get current agent
        sellers = await get_all_sellers()
        agent = next((s for s in sellers if s.get("id") == agent_id), None)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        old_name = agent.get("seller_name")
        
        # Update logic would go here (need to add update_seller function to database.py)
        # For now, we'll use existing functions
        if name and name != old_name:
            # Would need rename function
            pass
        
        if telegram_id and telegram_id != agent.get("telegram_id"):
            await link_seller_to_telegram(old_name, telegram_id)
        
        if is_active is not None and not is_active:
            await deactivate_seller(old_name)
        
        await log_action(
            user_type="admin",
            user_id=str(current_admin["id"]),
            user_name=current_admin.get("full_name") or current_admin["email"],
            action_type="agent_updated",
            details=f"Updated agent: {old_name}"
        )
        
        return JSONResponse({"success": True, "message": "Agent updated successfully"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@agents_router.delete("/api/agents/{agent_id}")
async def delete_agent(
    agent_id: int,
    reassign_to: Optional[str] = Form(None),
    current_admin: dict = Depends(auth.get_current_admin)
):
    """Delete a sales agent."""
    try:
        sellers = await get_all_sellers()
        agent = next((s for s in sellers if s.get("id") == agent_id), None)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        agent_name = agent.get("seller_name")
        
        # Reassign leads if needed
        if reassign_to:
            leads = await sheets_client.get_leads_by_seller(agent_name)
            for lead in leads:
                await sheets_client.update_lead(
                    lead.get("ID"),
                    {"Seller": reassign_to}
                )
        
        await deactivate_seller(agent_name)
        
        await log_action(
            user_type="admin",
            user_id=str(current_admin["id"]),
            user_name=current_admin.get("full_name") or current_admin["email"],
            action_type="agent_deleted",
            details=f"Deleted agent: {agent_name}"
        )
        
        return JSONResponse({"success": True, "message": "Agent deleted successfully"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== LEADS ROUTES ==========

@leads_router.get("/leads", response_class=HTMLResponse)
async def leads_page(request: Request, current_admin: dict = Depends(auth.get_current_admin)):
    """Leads management page."""
    return templates.TemplateResponse("leads.html", {"request": request, "admin": current_admin})


@leads_router.get("/api/leads")
async def get_leads(
    search: Optional[str] = None,
    status: Optional[str] = None,
    seller: Optional[str] = None,
    source: Optional[str] = None,
    sort_by: Optional[str] = "newest",
    current_admin: dict = Depends(auth.get_current_admin)
):
    """Get leads with filtering and sorting."""
    try:
        all_leads = await sheets_client.get_all_leads()
        
        # Filter
        filtered_leads = all_leads
        
        if search:
            search_lower = search.lower()
            filtered_leads = [
                lead for lead in filtered_leads
                if search_lower in lead.get("Name", "").lower() or
                   search_lower in lead.get("Phone", "").lower() or
                   search_lower in str(lead.get("ID", "")).lower()
            ]
        
        if status:
            filtered_leads = [lead for lead in filtered_leads if lead.get("Status") == status]
        
        if seller:
            filtered_leads = [lead for lead in filtered_leads if lead.get("Seller", "").lower() == seller.lower()]
        
        if source:
            filtered_leads = [lead for lead in filtered_leads if lead.get("Lead_Source", "").lower() == source.lower()]
        
        # Sort
        from utils.time_utils import parse_datetime
        
        if sort_by == "newest":
            filtered_leads.sort(
                key=lambda x: parse_datetime(x.get("Created_At", "2000-01-01")) if x.get("Created_At") else datetime.min,
                reverse=True
            )
        elif sort_by == "oldest":
            filtered_leads.sort(
                key=lambda x: parse_datetime(x.get("Created_At", "2000-01-01")) if x.get("Created_At") else datetime.max
            )
        elif sort_by == "seller":
            filtered_leads.sort(key=lambda x: x.get("Seller", ""))
        elif sort_by == "status":
            filtered_leads.sort(key=lambda x: x.get("Status", ""))
        
        return JSONResponse({"leads": filtered_leads, "total": len(filtered_leads)})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@leads_router.get("/api/leads/{lead_id}")
async def get_lead_detail(lead_id: str, current_admin: dict = Depends(auth.get_current_admin)):
    """Get detailed information about a lead."""
    try:
        all_leads = await sheets_client.get_all_leads()
        lead = next((l for l in all_leads if l.get("ID") == lead_id), None)
        
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        return JSONResponse({"lead": lead})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@leads_router.put("/api/leads/{lead_id}")
async def update_lead(
    lead_id: str,
    status: Optional[str] = Form(None),
    seller: Optional[str] = Form(None),
    comment: Optional[str] = Form(None),
    current_admin: dict = Depends(auth.get_current_admin)
):
    """Update a lead."""
    try:
        all_leads = await sheets_client.get_all_leads()
        lead = next((l for l in all_leads if l.get("ID") == lead_id), None)
        
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        updates = {}
        old_status = lead.get("Status")
        
        if status and status in VALID_STATUSES:
            updates["Status"] = status
        
        if seller:
            updates["Seller"] = seller
        
        if comment is not None:
            updates["Comment"] = comment
        
        if updates:
            success = await sheets_client.update_lead(lead_id, updates)
            if success:
                await log_action(
                    user_type="admin",
                    user_id=str(current_admin["id"]),
                    user_name=current_admin.get("full_name") or current_admin["email"],
                    action_type="lead_updated",
                    lead_id=lead_id,
                    old_value=old_status,
                    new_value=updates.get("Status", old_status),
                    details=str(updates)
                )
                return JSONResponse({"success": True, "message": "Lead updated successfully"})
            else:
                raise HTTPException(status_code=500, detail="Failed to update lead in Google Sheets")
        else:
            return JSONResponse({"success": False, "message": "No updates provided"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== KPI ROUTES ==========

@kpi_router.get("/kpi", response_class=HTMLResponse)
async def kpi_page(request: Request, current_admin: dict = Depends(auth.get_current_admin)):
    """KPI reports page."""
    return templates.TemplateResponse("kpi.html", {"request": request, "admin": current_admin})


@kpi_router.get("/api/kpi/sellers")
async def get_kpi_sellers(current_admin: dict = Depends(auth.get_current_admin)):
    """Get KPI for all sellers."""
    try:
        kpi_service = KPIService()
        seller_stats = await kpi_service.get_seller_stats()
        return JSONResponse({"stats": seller_stats})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@kpi_router.get("/api/kpi/export")
async def export_kpi(
    format: str = "csv",
    current_admin: dict = Depends(auth.get_current_admin)
):
    """Export KPI data."""
    try:
        from admin_backend.export_service import export_kpi_data
        return await export_kpi_data(format)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== STATS ROUTES ==========

@stats_router.get("/api/stats/charts")
async def get_chart_data(
    period: str = "week",
    current_admin: dict = Depends(auth.get_current_admin)
):
    """Get chart data for dashboard."""
    try:
        from admin_backend.stats_service import get_chart_data
        return await get_chart_data(period)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== LOGS ROUTES ==========

@logs_router.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request, current_admin: dict = Depends(auth.get_current_admin)):
    """System logs page."""
    return templates.TemplateResponse("logs.html", {"request": request, "admin": current_admin})


@logs_router.get("/api/logs")
async def get_logs(
    limit: int = 100,
    offset: int = 0,
    action_type: Optional[str] = None,
    user_type: Optional[str] = None,
    lead_id: Optional[str] = None,
    current_admin: dict = Depends(auth.get_current_admin)
):
    """Get system logs."""
    try:
        logs = await get_system_logs(limit, offset, action_type, user_type, lead_id)
        return JSONResponse({"logs": logs})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== SYNC ROUTES ==========

@sync_router.get("/sync", response_class=HTMLResponse)
async def sync_page(request: Request, current_admin: dict = Depends(auth.get_current_admin)):
    """Google Sheet sync status page."""
    return templates.TemplateResponse("sync.html", {"request": request, "admin": current_admin})


@sync_router.get("/api/sync/status")
async def get_sync_status(current_admin: dict = Depends(auth.get_current_admin)):
    """Get Google Sheet sync status."""
    try:
        status = await get_latest_sync_status()
        if not status:
            return JSONResponse({
                "sync_time": None,
                "status": "unknown",
                "rows_count": 0,
                "new_leads_count": 0
            })
        return JSONResponse(status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@sync_router.post("/api/sync/force")
async def force_sync(current_admin: dict = Depends(auth.get_current_admin)):
    """Force a Google Sheet sync."""
    try:
        all_leads = await sheets_client.get_all_leads()
        await save_sync_status("success", rows_count=len(all_leads))
        
        await log_action(
            user_type="admin",
            user_id=str(current_admin["id"]),
            user_name=current_admin.get("full_name") or current_admin["email"],
            action_type="sync_forced",
            details=f"Forced sync: {len(all_leads)} rows"
        )
        
        return JSONResponse({"success": True, "rows_count": len(all_leads)})
    except Exception as e:
        await save_sync_status("error", error_message=str(e))
        raise HTTPException(status_code=500, detail=str(e))

