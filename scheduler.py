"""
Scheduler module - handles background tasks and periodic reminders.
Uses APScheduler for task scheduling.
"""
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from config import SHEET_POLL_INTERVAL
from services.reminders import ReminderService
from services.lead_monitor import LeadMonitorService
from database import save_scheduler_job, mark_job_completed


class SchedulerManager:
    """Manages background scheduler tasks."""

    def __init__(self, bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        self.reminder_service = ReminderService()
        self.lead_monitor = LeadMonitorService()
        self._running = False

    async def start(self):
        """Start the scheduler."""
        if self._running:
            return

        # Schedule periodic lead monitoring (new leads and status changes)
        self.scheduler.add_job(
            self._monitor_leads_job,
            trigger=IntervalTrigger(seconds=SHEET_POLL_INTERVAL),
            id="monitor_leads",
            replace_existing=True,
            max_instances=1,
        )

        # Schedule periodic lead processing (reminders)
        self.scheduler.add_job(
            self._process_leads_job,
            trigger=IntervalTrigger(seconds=SHEET_POLL_INTERVAL),
            id="process_leads",
            replace_existing=True,
            max_instances=1,
        )

        # Schedule daily KPI reports (at 9 AM UTC)
        self.scheduler.add_job(
            self._daily_kpi_report,
            trigger="cron",
            hour=9,
            minute=0,
            id="daily_kpi",
            replace_existing=True,
        )

        # Schedule weekly KPI reports (Monday at 9 AM UTC)
        self.scheduler.add_job(
            self._weekly_kpi_report,
            trigger="cron",
            day_of_week="mon",
            hour=9,
            minute=0,
            id="weekly_kpi",
            replace_existing=True,
        )

        self.scheduler.start()
        self._running = True
        logger.info("Scheduler started")

    async def stop(self):
        """Stop the scheduler."""
        if not self._running:
            return

        self.scheduler.shutdown(wait=True)
        self._running = False
        logger.info("Scheduler stopped")

    async def _monitor_leads_job(self):
        """Periodic job to monitor for new leads and status changes."""
        try:
            logger.debug("Monitoring leads for changes...")
            changes = await self.lead_monitor.process_all_changes(self.bot)

            if changes["new_leads"] > 0 or changes["status_changes"] > 0:
                logger.info(
                    f"Detected {changes['new_leads']} new leads and "
                    f"{changes['status_changes']} status changes"
                )

        except Exception as e:
            logger.error(f"Error in monitor_leads_job: {e}")

    async def _process_leads_job(self):
        """Periodic job to process all leads and send reminders."""
        try:
            logger.debug("Processing leads for reminders...")
            reminders_sent = await self.reminder_service.process_all_leads(self.bot)

            if reminders_sent:
                logger.info(f"Sent {len(reminders_sent)} reminders")

        except Exception as e:
            logger.error(f"Error in process_leads_job: {e}")

    async def _daily_kpi_report(self):
        """Send daily KPI report to admins."""
        try:
            from services.kpi import KPIService
            from database import get_all_admins
            from config import ADMIN_IDS

            kpi_service = KPIService()
            dashboard = await kpi_service.get_dashboard()

            admins = await get_all_admins()
            admin_ids = [admin["telegram_id"] for admin in admins]
            admin_ids.extend(ADMIN_IDS)

            message = "📊 <b>Kunlik KPI Hisobot</b>\n\n"
            message += f"Jami Lidlar: {dashboard.get('total_leads', 0)}\n"
            message += f"Faol Lidlar: {dashboard.get('active_leads', 0)}\n"
            message += f"Kechiktirilgan Lidlar: {dashboard.get('overdue_leads', 0)}\n"
            message += f"Bugungi Lidlar: {dashboard.get('leads_today', 0)}\n"
            message += f"Shu Hafta Lidlar: {dashboard.get('leads_this_week', 0)}\n"

            for admin_id in set(admin_ids):
                try:
                    await self.bot.send_message(admin_id, message)
                except Exception as e:
                    logger.error(f"Error sending daily report to {admin_id}: {e}")

            logger.info("Daily KPI report sent")

        except Exception as e:
            logger.error(f"Error in daily_kpi_report: {e}")

    async def _weekly_kpi_report(self):
        """Send weekly KPI report to admins."""
        try:
            from services.kpi import KPIService
            from database import get_all_admins
            from config import ADMIN_IDS

            kpi_service = KPIService()
            stats = await kpi_service.get_all_stats()
            seller_stats = await kpi_service.get_seller_stats()

            admins = await get_all_admins()
            admin_ids = [admin["telegram_id"] for admin in admins]
            admin_ids.extend(ADMIN_IDS)

            message = "📈 <b>Haftalik KPI Hisobot</b>\n\n"

            message += "<b>Umumiy Ko'rsatkichlar:</b>\n"
            message += f"Qo'ng'iroq #1 Bajarilishi: {stats.get('call1_completion_rate', 0):.1f}%\n"
            message += f"Qo'ng'iroq #2 Bajarilishi: {stats.get('call2_completion_rate', 0):.1f}%\n"
            message += f"Qo'ng'iroq #3 Bajarilishi: {stats.get('call3_completion_rate', 0):.1f}%\n"
            message += f"Umumiy Konversiya: {stats.get('overall_conversion_rate', 0):.1f}%\n\n"

            message += "<b>Eng Yaxshi Sotuvchilar:</b>\n"
            for seller_name, seller_data in list(seller_stats.items())[:5]:
                message += f"{seller_name}: {seller_data.get('conversion_rate', 0):.1f}% konversiya\n"

            for admin_id in set(admin_ids):
                try:
                    await self.bot.send_message(admin_id, message)
                except Exception as e:
                    logger.error(f"Error sending weekly report to {admin_id}: {e}")

            logger.info("Weekly KPI report sent")

        except Exception as e:
            logger.error(f"Error in weekly_kpi_report: {e}")

