"""
Statistics service for generating chart data.
"""
from typing import Dict, List
from datetime import datetime, timedelta
from collections import defaultdict

from google_sheets import sheets_client
from utils.time_utils import parse_datetime, now_utc


async def get_chart_data(period: str = "week") -> Dict:
    """Get chart data for the specified period."""
    all_leads = await sheets_client.get_all_leads()
    
    # Determine date range
    end_date = now_utc().date()
    if period == "week":
        start_date = end_date - timedelta(days=7)
    elif period == "month":
        start_date = end_date - timedelta(days=30)
    else:
        start_date = end_date - timedelta(days=7)
    
    # Filter leads in date range
    filtered_leads = []
    for lead in all_leads:
        if lead.get("Created_At"):
            try:
                lead_date = parse_datetime(lead["Created_At"]).date()
                if start_date <= lead_date <= end_date:
                    filtered_leads.append(lead)
            except:
                pass
    
    # Leads by source (Manba)
    source_counts = defaultdict(int)
    for lead in all_leads:
        source = lead.get("Lead_Source", "Unknown")
        source_counts[source] += 1
    
    # Leads per sales agent
    agent_counts = defaultdict(int)
    for lead in all_leads:
        agent = lead.get("Seller", "Unassigned")
        agent_counts[agent] += 1
    
    # 7-day activity (calls, follow-ups, sales)
    daily_activity = defaultdict(lambda: {"calls": 0, "followups": 0, "sales": 0})
    
    for lead in filtered_leads:
        lead_date = parse_datetime(lead.get("Created_At", "2000-01-01")).date() if lead.get("Created_At") else None
        if not lead_date:
            continue
        
        # Count calls
        if lead.get("Call_1_Time") or lead.get("Call_2_Time") or lead.get("Call_3_Time"):
            daily_activity[lead_date]["calls"] += 1
        
        # Count follow-ups
        if lead.get("Next_Followup"):
            try:
                followup_date = parse_datetime(lead["Next_Followup"]).date()
                if start_date <= followup_date <= end_date:
                    daily_activity[followup_date]["followups"] += 1
            except:
                pass
        
        # Count sales (First Class Confirmed)
        if lead.get("Status") == "First Class Confirmed":
            daily_activity[lead_date]["sales"] += 1
    
    # Convert to lists for Chart.js
    dates = sorted(daily_activity.keys())
    calls_data = [daily_activity[date]["calls"] for date in dates]
    followups_data = [daily_activity[date]["followups"] for date in dates]
    sales_data = [daily_activity[date]["sales"] for date in dates]
    
    return {
        "sources": {
            "labels": list(source_counts.keys()),
            "data": list(source_counts.values())
        },
        "agents": {
            "labels": list(agent_counts.keys()),
            "data": list(agent_counts.values())
        },
        "activity": {
            "labels": [date.strftime("%Y-%m-%d") for date in dates],
            "calls": calls_data,
            "followups": followups_data,
            "sales": sales_data
        }
    }

