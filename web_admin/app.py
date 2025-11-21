"""
Web Admin Panel for Lead Manager Bot.
Flask-based web interface for viewing seller statistics and managing sellers.
"""
from flask import Flask, render_template, jsonify, request
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List

from database import (
    get_all_sellers,
    get_seller_by_name,
    get_seller_by_telegram,
    add_seller_record,
    link_seller_to_telegram,
    deactivate_seller,
)
from google_sheets import sheets_client
from services.kpi import KPIService
from config import ADMIN_IDS

app = Flask(__name__)


def run_async(coro):
    """Run async function in sync context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('dashboard.html')


@app.route('/api/sellers')
def api_sellers():
    """Get all sellers with statistics."""
    try:
        sellers = run_async(get_all_sellers())
        kpi_service = KPIService()
        stats = run_async(kpi_service.get_seller_stats())
        
        sellers_data = []
        for seller in sellers:
            seller_name = seller.get("seller_name", "")
            seller_stats = stats.get(seller_name, {})
            
            # Get leads for this seller
            leads = run_async(sheets_client.get_leads_by_seller(seller_name))
            
            sellers_data.append({
                "id": seller.get("id"),
                "name": seller_name,
                "telegram_id": seller.get("telegram_id"),
                "is_active": bool(seller.get("is_active")),
                "is_linked": seller.get("telegram_id") is not None,
                "total_leads": len(leads),
                "stats": seller_stats,
                "created_at": seller.get("created_at"),
            })
        
        return jsonify({"sellers": sellers_data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/seller/<seller_name>')
def api_seller_detail(seller_name: str):
    """Get detailed information about a specific seller."""
    try:
        seller = run_async(get_seller_by_name(seller_name))
        if not seller:
            return jsonify({"error": "Seller not found"}), 404
        
        # Get leads
        leads = run_async(sheets_client.get_leads_by_seller(seller_name))
        
        # Get KPI stats
        kpi_service = KPIService()
        stats = run_async(kpi_service.get_seller_stats())
        seller_stats = stats.get(seller_name, {})
        
        # Group leads by status
        leads_by_status = {}
        for lead in leads:
            status = lead.get("Status", "Unknown")
            if status not in leads_by_status:
                leads_by_status[status] = []
            leads_by_status[status].append(lead)
        
        return jsonify({
            "seller": {
                "id": seller.get("id"),
                "name": seller.get("seller_name"),
                "telegram_id": seller.get("telegram_id"),
                "is_active": bool(seller.get("is_active")),
                "created_at": seller.get("created_at"),
            },
            "leads": leads,
            "leads_by_status": leads_by_status,
            "stats": seller_stats,
            "total_leads": len(leads),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/seller/add', methods=['POST'])
def api_add_seller():
    """Add a new seller."""
    try:
        data = request.json
        seller_name = data.get("name", "").strip()
        telegram_id = data.get("telegram_id")
        
        if not seller_name:
            return jsonify({"error": "Seller name is required"}), 400
        
        # Check if seller already exists
        existing = run_async(get_seller_by_name(seller_name))
        if existing:
            return jsonify({"error": f"Seller '{seller_name}' already exists"}), 400
        
        # Add seller
        run_async(add_seller_record(seller_name, telegram_id=telegram_id))
        
        # Get leads count
        leads = run_async(sheets_client.get_leads_by_seller(seller_name))
        
        return jsonify({
            "success": True,
            "message": f"Seller '{seller_name}' added successfully",
            "leads_count": len(leads),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/seller/link', methods=['POST'])
def api_link_seller():
    """Link a seller to Telegram ID."""
    try:
        data = request.json
        seller_name = data.get("name", "").strip()
        telegram_id = data.get("telegram_id")
        
        if not seller_name or not telegram_id:
            return jsonify({"error": "Seller name and Telegram ID are required"}), 400
        
        # Check if seller exists
        seller = run_async(get_seller_by_name(seller_name))
        if not seller:
            return jsonify({"error": f"Seller '{seller_name}' not found"}), 404
        
        # Link seller
        success = run_async(link_seller_to_telegram(seller_name, telegram_id))
        
        if success:
            return jsonify({
                "success": True,
                "message": f"Seller '{seller_name}' linked to Telegram ID {telegram_id}",
            })
        else:
            return jsonify({"error": "Failed to link seller"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/overview')
def api_overview():
    """Get overall statistics."""
    try:
        kpi_service = KPIService()
        dashboard = run_async(kpi_service.get_dashboard())
        all_stats = run_async(kpi_service.get_all_stats())
        
        return jsonify({
            "dashboard": dashboard,
            "stats": all_stats,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

