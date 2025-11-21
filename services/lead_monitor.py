"""
Lead monitoring service - detects new leads and status changes in Google Sheets.
Sends notifications to sellers when their leads are updated.
"""
from typing import List, Dict, Optional, Set
from datetime import datetime
from loguru import logger

from google_sheets import sheets_client
from database import (
    get_lead_state,
    update_lead_state,
    get_seller_by_name,
    get_all_sellers,
)
from services.reminders import ReminderService
from config import STATUS_NEW_LEAD, STATUS_CALL1_NEEDED
from utils.time_utils import now_utc, format_datetime, parse_datetime


class LeadMonitorService:
    """Service for monitoring leads and notifying sellers of changes."""

    def __init__(self):
        self.reminder_service = ReminderService()

    async def check_for_new_leads(self, bot) -> List[Dict]:
        """
        Check for new leads and notify sellers.
        Returns list of new leads detected.
        """
        try:
            current_leads = await sheets_client.get_all_leads()
            new_leads = []

            for lead in current_leads:
                lead_id = lead.get("ID", "")
                if not lead_id:
                    continue

                # Check if this is a new lead
                last_state = await get_lead_state(lead_id)
                
                if not last_state:
                    # This is a new lead - never seen before
                    await self._handle_new_lead(lead, bot)
                    await update_lead_state(lead_id, lead.get("Status", ""))
                    new_leads.append(lead)
                    logger.info(f"New lead detected: {lead_id}")

            return new_leads

        except Exception as e:
            logger.error(f"Error checking for new leads: {e}")
            return []

    async def check_for_status_changes(self, bot) -> List[Dict]:
        """
        Check for status changes in existing leads.
        Returns list of leads with changed status.
        """
        try:
            current_leads = await sheets_client.get_all_leads()
            changed_leads = []

            for lead in current_leads:
                lead_id = lead.get("ID", "")
                if not lead_id:
                    continue

                current_status = lead.get("Status", "")
                last_state = await get_lead_state(lead_id)

                if last_state:
                    last_status = last_state.get("last_status", "")
                    
                    # Check if status changed
                    if current_status != last_status and current_status:
                        await self._handle_status_change(lead, last_status, current_status, bot)
                        await update_lead_state(lead_id, current_status)
                        changed_leads.append(lead)
                        logger.info(f"Status change detected for lead {lead_id}: {last_status} -> {current_status}")

            return changed_leads

        except Exception as e:
            logger.error(f"Error checking for status changes: {e}")
            return []

    async def _handle_new_lead(self, lead: Dict, bot):
        """Handle a newly detected lead."""
        seller_name = lead.get("Seller", "").strip()
        if not seller_name:
            logger.warning(f"Lead {lead.get('ID')} has no seller assigned")
            return

        # Get seller from database
        seller = await get_seller_by_name(seller_name)
        if not seller:
            logger.warning(f"Seller '{seller_name}' not found in database for lead {lead.get('ID')}")
            return

        telegram_id = seller.get("telegram_id")
        if not telegram_id:
            logger.warning(f"Seller '{seller_name}' not linked to Telegram for lead {lead.get('ID')}")
            return

        # Check if status needs to be updated
        current_status = lead.get("Status", "").strip()
        if current_status == STATUS_NEW_LEAD or not current_status:
            # Auto-update to Call #1 Needed and set Call #1 time
            await sheets_client.update_lead(lead.get("ID"), {
                "Status": STATUS_CALL1_NEEDED,
                "Call_1_Time": format_datetime(now_utc())
            })
            current_status = STATUS_CALL1_NEEDED

        # Send notification to seller
        await self._send_new_lead_notification(lead, telegram_id, bot, current_status)

    async def _handle_status_change(self, lead: Dict, old_status: str, new_status: str, bot):
        """Handle a status change in a lead."""
        seller_name = lead.get("Seller", "").strip()
        if not seller_name:
            return

        # Get seller from database
        seller = await get_seller_by_name(seller_name)
        if not seller:
            return

        telegram_id = seller.get("telegram_id")
        if not telegram_id:
            return

        # Send notification to seller
        await self._send_status_change_notification(lead, old_status, new_status, telegram_id, bot)

        # Trigger reminder service to handle status change
        await self.reminder_service.handle_status_change(lead.get("ID"), new_status)

    async def _send_new_lead_notification(self, lead: Dict, telegram_id: int, bot, status: str):
        """Send notification to seller about new lead."""
        lead_id = lead.get("ID", "N/A")
        name = lead.get("Name", "N/A")
        phone = lead.get("Phone", "N/A")
        source = lead.get("Lead_Source", "N/A")

        message = f"🆕 <b>Yangi Lid Qo'shildi!</b>\n\n"
        message += f"<b>Lid ID:</b> {lead_id}\n"
        message += f"<b>Ism:</b> {name}\n"
        message += f"<b>Telefon:</b> {phone}\n"
        if source != "N/A":
            message += f"<b>Manba:</b> {source}\n"
        message += f"<b>Holat:</b> {status}\n\n"
        message += "Iltimos, birinchi qo'ng'iroqni qiling!"

        try:
            await bot.send_message(telegram_id, message)
            logger.info(f"Sent new lead notification to seller {telegram_id} for lead {lead_id}")
        except Exception as e:
            logger.error(f"Error sending new lead notification to {telegram_id}: {e}")

    async def _send_status_change_notification(self, lead: Dict, old_status: str, new_status: str, telegram_id: int, bot):
        """Send notification to seller about status change."""
        lead_id = lead.get("ID", "N/A")
        name = lead.get("Name", "N/A")

        # Only notify for significant status changes
        significant_changes = [
            STATUS_CALL1_DONE,
            STATUS_CALL2_DONE,
            STATUS_CALL3_DONE,
            STATUS_FIRST_CLASS_SCHEDULED,
            STATUS_FIRST_CLASS_CONFIRMED,
            STATUS_FOLLOWUP_NEEDED,
        ]

        if new_status not in significant_changes:
            return

        message = f"🔄 <b>Lid Holati O'zgardi</b>\n\n"
        message += f"<b>Lid ID:</b> {lead_id}\n"
        message += f"<b>Ism:</b> {name}\n"
        message += f"<b>Eski Holat:</b> {old_status}\n"
        message += f"<b>Yangi Holat:</b> {new_status}\n\n"

        # Add context based on new status
        if new_status == STATUS_CALL1_DONE:
            message += "✅ Qo'ng'iroq #1 bajarildi. Qo'ng'iroq #2 2 soatdan keyin rejalashtiriladi."
        elif new_status == STATUS_CALL2_DONE:
            message += "✅ Qo'ng'iroq #2 bajarildi. Qo'ng'iroq #3 24 soatdan keyin rejalashtiriladi."
        elif new_status == STATUS_FIRST_CLASS_SCHEDULED:
            message += "📅 Birinchi dars rejalashtirildi. Eslatmalar yuboriladi."
        elif new_status == STATUS_FOLLOWUP_NEEDED:
            message += "⚠️ Qayta aloqa kerak. Iltimos, keyingi qadamni amalga oshiring."

        try:
            await bot.send_message(telegram_id, message)
            logger.info(f"Sent status change notification to seller {telegram_id} for lead {lead_id}")
        except Exception as e:
            logger.error(f"Error sending status change notification to {telegram_id}: {e}")

    async def process_all_changes(self, bot) -> Dict:
        """
        Process all changes (new leads and status changes).
        Returns summary of changes detected.
        """
        new_leads = await self.check_for_new_leads(bot)
        changed_leads = await self.check_for_status_changes(bot)

        return {
            "new_leads": len(new_leads),
            "status_changes": len(changed_leads),
            "new_leads_list": new_leads,
            "changed_leads_list": changed_leads,
        }

