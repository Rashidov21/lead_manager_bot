"""
KPI Analytics Service - calculates and provides analytics for admins.
"""
from typing import Dict, List
from collections import defaultdict
from datetime import datetime, timedelta
from loguru import logger

from google_sheets import sheets_client
from config import (
    STATUS_CALL1_NEEDED,
    STATUS_CALL1_DONE,
    STATUS_CALL2_DONE,
    STATUS_CALL3_DONE,
    STATUS_FIRST_CLASS_PENDING,
    STATUS_COMPLETED,
    STATUS_LOST,
)
from utils.time_utils import parse_datetime, now_utc, days_between


class KPIService:
    """Service for calculating KPI metrics and analytics."""

    def __init__(self):
        pass

    async def get_dashboard(self) -> Dict:
        """Get dashboard data with key metrics."""
        try:
            leads = await sheets_client.get_all_leads()
            now = now_utc()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = today_start - timedelta(days=now.weekday())

            # Calculate metrics
            total_leads = len(leads)
            active_leads = len([l for l in leads if l.get("Status") not in [STATUS_COMPLETED, STATUS_LOST]])

            # Overdue leads (Call #1 Needed for > 12h)
            overdue_leads = 0
            for lead in leads:
                if lead.get("Status") == STATUS_CALL1_NEEDED:
                    created_at = parse_datetime(lead.get("Created_At", ""))
                    if created_at and days_between(created_at, now) > 0.5:
                        overdue_leads += 1

            # Leads today
            leads_today = 0
            for lead in leads:
                created_at = parse_datetime(lead.get("Created_At", ""))
                if created_at and created_at >= today_start:
                    leads_today += 1

            # Leads this week
            leads_this_week = 0
            seller_weekly = defaultdict(int)
            for lead in leads:
                created_at = parse_datetime(lead.get("Created_At", ""))
                if created_at and created_at >= week_start:
                    leads_this_week += 1
                    seller_name = lead.get("Seller", "")
                    if seller_name:
                        seller_weekly[seller_name] += 1

            # Top sellers
            top_sellers = [
                {"name": name, "leads": count}
                for name, count in sorted(seller_weekly.items(), key=lambda x: x[1], reverse=True)
            ]

            # Recent alerts (overdue leads)
            recent_alerts = []
            for lead in leads:
                if lead.get("Status") == STATUS_CALL1_NEEDED:
                    created_at = parse_datetime(lead.get("Created_At", ""))
                    if created_at and days_between(created_at, now) > 0.5:
                        recent_alerts.append(
                            f"Lead {lead.get('ID', 'N/A')} - Call #1 overdue ({lead.get('Seller', 'N/A')})"
                        )

            return {
                "total_leads": total_leads,
                "active_leads": active_leads,
                "overdue_leads": overdue_leads,
                "leads_today": leads_today,
                "leads_this_week": leads_this_week,
                "top_sellers": top_sellers,
                "recent_alerts": recent_alerts[:10],
            }

        except Exception as e:
            logger.error(f"Error calculating dashboard: {e}")
            return {}

    async def get_all_stats(self) -> Dict:
        """Get comprehensive statistics."""
        try:
            leads = await sheets_client.get_all_leads()

            # Calculate completion rates
            total = len(leads)
            call1_done = len([l for l in leads if l.get("Status") in [STATUS_CALL1_DONE, STATUS_CALL2_DONE, STATUS_CALL3_DONE, STATUS_COMPLETED]])
            call2_done = len([l for l in leads if l.get("Status") in [STATUS_CALL2_DONE, STATUS_CALL3_DONE, STATUS_COMPLETED]])
            call3_done = len([l for l in leads if l.get("Status") in [STATUS_CALL3_DONE, STATUS_COMPLETED]])
            first_class_attended = len([l for l in leads if l.get("Status") == STATUS_COMPLETED])
            converted = len([l for l in leads if l.get("Status") == STATUS_COMPLETED])

            call1_rate = (call1_done / total * 100) if total > 0 else 0
            call2_rate = (call2_done / total * 100) if total > 0 else 0
            call3_rate = (call3_done / total * 100) if total > 0 else 0
            first_class_rate = (first_class_attended / total * 100) if total > 0 else 0
            conversion_rate = (converted / total * 100) if total > 0 else 0

            # Lead sources
            sources = defaultdict(int)
            for lead in leads:
                source = lead.get("Lead_Source", "Unknown")
                sources[source] += 1

            # Daily stats (last 30 days)
            now = now_utc()
            daily_stats = []
            for i in range(30):
                day = now - timedelta(days=i)
                day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = day_start + timedelta(days=1)

                day_leads = 0
                for lead in leads:
                    created_at = parse_datetime(lead.get("Created_At", ""))
                    if created_at and day_start <= created_at < day_end:
                        day_leads += 1

                daily_stats.append({
                    "date": day_start.strftime("%Y-%m-%d"),
                    "leads": day_leads
                })

            daily_stats.reverse()

            return {
                "call1_completion_rate": call1_rate,
                "call2_completion_rate": call2_rate,
                "call3_completion_rate": call3_rate,
                "first_class_attendance_rate": first_class_rate,
                "overall_conversion_rate": conversion_rate,
                "lead_sources": dict(sources),
                "daily_stats": daily_stats,
            }

        except Exception as e:
            logger.error(f"Error calculating all stats: {e}")
            return {}

    async def get_seller_stats(self) -> Dict[str, Dict]:
        """Get statistics per seller."""
        try:
            leads = await sheets_client.get_all_leads()

            seller_data = defaultdict(lambda: {
                "total_leads": 0,
                "call1_done": 0,
                "call2_done": 0,
                "call3_done": 0,
                "first_class_attended": 0,
                "converted": 0,
            })

            for lead in leads:
                seller_name = lead.get("Seller", "")
                if not seller_name:
                    continue

                status = lead.get("Status", "")
                seller_data[seller_name]["total_leads"] += 1

                if status in [STATUS_CALL1_DONE, STATUS_CALL2_DONE, STATUS_CALL3_DONE, STATUS_COMPLETED]:
                    seller_data[seller_name]["call1_done"] += 1

                if status in [STATUS_CALL2_DONE, STATUS_CALL3_DONE, STATUS_COMPLETED]:
                    seller_data[seller_name]["call2_done"] += 1

                if status in [STATUS_CALL3_DONE, STATUS_COMPLETED]:
                    seller_data[seller_name]["call3_done"] += 1

                if status == STATUS_COMPLETED:
                    seller_data[seller_name]["first_class_attended"] += 1
                    seller_data[seller_name]["converted"] += 1

            # Calculate rates
            result = {}
            for seller_name, data in seller_data.items():
                total = data["total_leads"]
                result[seller_name] = {
                    "total_leads": total,
                    "call1_completion_rate": (data["call1_done"] / total * 100) if total > 0 else 0,
                    "call2_completion_rate": (data["call2_done"] / total * 100) if total > 0 else 0,
                    "call3_completion_rate": (data["call3_done"] / total * 100) if total > 0 else 0,
                    "first_class_attendance_rate": (data["first_class_attended"] / total * 100) if total > 0 else 0,
                    "conversion_rate": (data["converted"] / total * 100) if total > 0 else 0,
                }

            return result

        except Exception as e:
            logger.error(f"Error calculating seller stats: {e}")
            return {}

