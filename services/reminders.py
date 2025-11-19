"""
Reminder service - handles all reminder logic based on lead status.
"""
from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger

from google_sheets import sheets_client
from database import mark_reminder_sent, was_reminder_sent, update_lead_state
from config import (
    STATUS_CALL1_NEEDED,
    STATUS_CALL1_DONE,
    STATUS_CALL2_DONE,
    STATUS_CALL3_DONE,
    STATUS_FIRST_CLASS_PENDING,
    STATUS_DID_NOT_ATTEND,
    REMINDER_CALL1_1H,
    REMINDER_CALL1_2H,
    REMINDER_CALL1_12H,
    REMINDER_CALL2_DELAY,
    REMINDER_CALL3_DELAY,
    REMINDER_FIRST_CLASS_24H,
    REMINDER_FIRST_CLASS_2H,
)
from utils.time_utils import (
    now_utc,
    parse_datetime,
    format_datetime,
    add_seconds,
    add_hours,
    time_until,
    is_past,
    hours_between,
)


class ReminderService:
    """Service for managing reminders and status-based scheduling."""

    def __init__(self):
        pass

    async def process_all_leads(self, bot) -> List[Dict]:
        """
        Process all leads and send appropriate reminders.
        Returns list of reminders sent.
        """
        try:
            leads = await sheets_client.get_all_leads()
            reminders_sent = []

            for lead in leads:
                lead_reminders = await self.process_lead(lead, bot)
                reminders_sent.extend(lead_reminders)

            return reminders_sent

        except Exception as e:
            logger.error(f"Error processing leads: {e}")
            return []

    async def process_lead(self, lead: Dict, bot) -> List[Dict]:
        """Process a single lead and send reminders if needed."""
        reminders_sent = []

        lead_id = lead.get("ID", "")
        status = lead.get("Status", "")
        seller_name = lead.get("Seller", "")

        if not lead_id or not status:
            return reminders_sent

        # Update lead state in database
        await update_lead_state(lead_id, status)

        # Process based on status
        if status == STATUS_CALL1_NEEDED:
            reminders = await self._handle_call1_needed(lead, bot)
            reminders_sent.extend(reminders)

        elif status == STATUS_CALL1_DONE:
            reminders = await self._handle_call1_done(lead, bot)
            reminders_sent.extend(reminders)

        elif status == STATUS_CALL2_DONE:
            reminders = await self._handle_call2_done(lead, bot)
            reminders_sent.extend(reminders)

        elif status == STATUS_FIRST_CLASS_PENDING:
            reminders = await self._handle_first_class_pending(lead, bot)
            reminders_sent.extend(reminders)

        elif status == STATUS_DID_NOT_ATTEND:
            reminders = await self._handle_did_not_attend(lead, bot)
            reminders_sent.extend(reminders)

        return reminders_sent

    async def _handle_call1_needed(self, lead: Dict, bot) -> List[Dict]:
        """Handle reminders for Call #1 Needed status."""
        reminders_sent = []
        lead_id = lead.get("ID", "")
        created_at_str = lead.get("Created_At", "")

        if not created_at_str:
            return reminders_sent

        created_at = parse_datetime(created_at_str)
        if not created_at:
            return reminders_sent

        now = now_utc()
        hours_since_creation = hours_between(created_at, now)

        # 1 hour reminder
        if hours_since_creation >= 1:
            reminder_key = f"{lead_id}_call1_1h"
            scheduled_time = format_datetime(add_hours(created_at, 1))

            if not await was_reminder_sent(lead_id, "call1_1h", scheduled_time):
                await self._send_call1_reminder(lead, bot, "1 hour", reminder_key)
                await mark_reminder_sent(lead_id, "call1_1h", scheduled_time)
                reminders_sent.append({"type": "call1_1h", "lead_id": lead_id})

        # 2 hour reminder
        if hours_since_creation >= 2:
            reminder_key = f"{lead_id}_call1_2h"
            scheduled_time = format_datetime(add_hours(created_at, 2))

            if not await was_reminder_sent(lead_id, "call1_2h", scheduled_time):
                await self._send_call1_reminder(lead, bot, "2 hours", reminder_key)
                await mark_reminder_sent(lead_id, "call1_2h", scheduled_time)
                reminders_sent.append({"type": "call1_2h", "lead_id": lead_id})

        # 12 hour escalation to admin
        if hours_since_creation >= 12:
            reminder_key = f"{lead_id}_call1_12h"
            scheduled_time = format_datetime(add_hours(created_at, 12))

            if not await was_reminder_sent(lead_id, "call1_12h", scheduled_time):
                await self._send_call1_escalation(lead, bot, reminder_key)
                await mark_reminder_sent(lead_id, "call1_12h", scheduled_time)
                reminders_sent.append({"type": "call1_12h", "lead_id": lead_id})

        return reminders_sent

    async def _handle_call1_done(self, lead: Dict, bot) -> List[Dict]:
        """Handle Call #1 Done - schedule Call #2."""
        reminders_sent = []
        lead_id = lead.get("ID", "")
        call1_time_str = lead.get("Call_1_Time", "")

        # If Call_1_Time is not set, set it to now
        if not call1_time_str:
            call1_time = now_utc()
            await sheets_client.update_call_time(lead_id, 1, call1_time)
        else:
            call1_time = parse_datetime(call1_time_str)
            if not call1_time:
                call1_time = now_utc()

        # Check if Call #2 is scheduled
        call2_time_str = lead.get("Call_2_Time", "")
        if not call2_time_str:
            # Schedule Call #2 for 2 hours after Call #1
            call2_time = add_seconds(call1_time, REMINDER_CALL2_DELAY)
            await sheets_client.update_call_time(lead_id, 2, call2_time)

            # Send notification to seller
            await self._send_call2_scheduled(lead, bot, call2_time)
            reminders_sent.append({"type": "call2_scheduled", "lead_id": lead_id})

        # Check if Call #2 is due
        if call2_time_str:
            call2_time = parse_datetime(call2_time_str)
            if call2_time and is_past(call2_time):
                reminder_key = f"{lead_id}_call2_due"
                scheduled_time = format_datetime(call2_time)

                if not await was_reminder_sent(lead_id, "call2_due", scheduled_time):
                    await self._send_call2_reminder(lead, bot, reminder_key)
                    await mark_reminder_sent(lead_id, "call2_due", scheduled_time)
                    reminders_sent.append({"type": "call2_due", "lead_id": lead_id})

        return reminders_sent

    async def _handle_call2_done(self, lead: Dict, bot) -> List[Dict]:
        """Handle Call #2 Done - schedule Call #3."""
        reminders_sent = []
        lead_id = lead.get("ID", "")
        call2_time_str = lead.get("Call_2_Time", "")

        if not call2_time_str:
            call2_time = now_utc()
            await sheets_client.update_call_time(lead_id, 2, call2_time)
        else:
            call2_time = parse_datetime(call2_time_str)
            if not call2_time:
                call2_time = now_utc()

        # Check if Call #3 is scheduled
        call3_time_str = lead.get("Call_3_Time", "")
        if not call3_time_str:
            # Schedule Call #3 for 24 hours after Call #2
            call3_time = add_seconds(call2_time, REMINDER_CALL3_DELAY)
            await sheets_client.update_call_time(lead_id, 3, call3_time)

            # Send notification to seller
            await self._send_call3_scheduled(lead, bot, call3_time)
            reminders_sent.append({"type": "call3_scheduled", "lead_id": lead_id})

        # Check if Call #3 is due
        if call3_time_str:
            call3_time = parse_datetime(call3_time_str)
            if call3_time and is_past(call3_time):
                reminder_key = f"{lead_id}_call3_due"
                scheduled_time = format_datetime(call3_time)

                if not await was_reminder_sent(lead_id, "call3_due", scheduled_time):
                    await self._send_call3_reminder(lead, bot, reminder_key)
                    await mark_reminder_sent(lead_id, "call3_due", scheduled_time)
                    reminders_sent.append({"type": "call3_due", "lead_id": lead_id})

        return reminders_sent

    async def _handle_first_class_pending(self, lead: Dict, bot) -> List[Dict]:
        """Handle First Class Pending Confirmation reminders."""
        reminders_sent = []
        lead_id = lead.get("ID", "")
        first_class_date_str = lead.get("First_Class_Date", "")

        if not first_class_date_str:
            return reminders_sent

        first_class_date = parse_datetime(first_class_date_str)
        if not first_class_date:
            return reminders_sent

        now = now_utc()
        time_until_class = time_until(first_class_date)
        hours_until = time_until_class.total_seconds() / 3600

        # 24 hours before reminder
        if 23 <= hours_until <= 25:
            reminder_key = f"{lead_id}_first_class_24h"
            scheduled_time = format_datetime(add_hours(first_class_date, -24))

            if not await was_reminder_sent(lead_id, "first_class_24h", scheduled_time):
                await self._send_first_class_reminder(lead, bot, "24 hours", reminder_key)
                await mark_reminder_sent(lead_id, "first_class_24h", scheduled_time)
                reminders_sent.append({"type": "first_class_24h", "lead_id": lead_id})

        # 2 hours before reminder
        if 1.5 <= hours_until <= 2.5:
            reminder_key = f"{lead_id}_first_class_2h"
            scheduled_time = format_datetime(add_hours(first_class_date, -2))

            if not await was_reminder_sent(lead_id, "first_class_2h", scheduled_time):
                await self._send_first_class_reminder(lead, bot, "2 hours", reminder_key)
                await mark_reminder_sent(lead_id, "first_class_2h", scheduled_time)
                reminders_sent.append({"type": "first_class_2h", "lead_id": lead_id})

        return reminders_sent

    async def _handle_did_not_attend(self, lead: Dict, bot) -> List[Dict]:
        """Handle Did Not Attend First Class - notify seller."""
        reminders_sent = []
        lead_id = lead.get("ID", "")
        reminder_key = f"{lead_id}_did_not_attend"

        # Send one-time notification
        if not await was_reminder_sent(lead_id, "did_not_attend", format_datetime(now_utc())):
            await self._send_did_not_attend_notification(lead, bot, reminder_key)
            await mark_reminder_sent(lead_id, "did_not_attend", format_datetime(now_utc()))
            reminders_sent.append({"type": "did_not_attend", "lead_id": lead_id})

        return reminders_sent

    async def handle_status_change(self, lead_id: str, new_status: str):
        """Handle status change - trigger appropriate actions."""
        lead = await sheets_client.get_lead_by_id(lead_id)
        if not lead:
            return

        # Update timestamps based on status
        if new_status == STATUS_CALL1_DONE:
            await sheets_client.update_call_time(lead_id, 1, now_utc())
        elif new_status == STATUS_CALL2_DONE:
            await sheets_client.update_call_time(lead_id, 2, now_utc())
        elif new_status == STATUS_CALL3_DONE:
            await sheets_client.update_call_time(lead_id, 3, now_utc())

    # Message sending methods
    async def _send_call1_reminder(self, lead: Dict, bot, time_str: str, reminder_key: str):
        """Send Call #1 reminder to seller."""
        from database import get_all_sellers

        seller_name = lead.get("Seller", "")
        sellers = await get_all_sellers()
        seller = next((s for s in sellers if s.get("full_name") == seller_name or s.get("username") == seller_name), None)

        if not seller:
            logger.warning(f"Seller {seller_name} not found for reminder")
            return

        telegram_id = seller["telegram_id"]
        lead_id = lead.get("ID", "")
        name = lead.get("Name", "")
        phone = lead.get("Phone", "")

        message = f"⏰ <b>Eslatma: Qo'ng'iroq #1 Kerak</b>\n\n"
        message += f"Lid ID: {lead_id}\n"
        message += f"Ism: {name}\n"
        message += f"Telefon: {phone}\n"
        message += f"Yaratilganidan beri: {time_str}\n\n"
        message += "Iltimos, birinchi qo'ng'iroqni qiling!"

        try:
            await bot.send_message(telegram_id, message)
            logger.info(f"Sent Call #1 reminder to seller {telegram_id} for lead {lead_id}")
        except Exception as e:
            logger.error(f"Error sending reminder to {telegram_id}: {e}")

    async def _send_call1_escalation(self, lead: Dict, bot, reminder_key: str):
        """Send Call #1 escalation to admin."""
        from database import get_all_admins
        from config import ADMIN_IDS

        admins = await get_all_admins()
        admin_ids = [admin["telegram_id"] for admin in admins]
        admin_ids.extend(ADMIN_IDS)  # Add from config

        lead_id = lead.get("ID", "")
        name = lead.get("Name", "")
        seller_name = lead.get("Seller", "")

        message = f"🚨 <b>Eskalatsiya: Qo'ng'iroq #1 Kechikdi</b>\n\n"
        message += f"Lid ID: {lead_id}\n"
        message += f"Ism: {name}\n"
        message += f"Sotuvchi: {seller_name}\n"
        message += f"Holat: {lead.get('Status', '')}\n\n"
        message += "⚠️ Qo'ng'iroq #1 12 soatdan ko'proq vaqt davomida kutilmoqda!"

        for admin_id in set(admin_ids):
            try:
                await bot.send_message(admin_id, message)
                logger.info(f"Sent escalation to admin {admin_id} for lead {lead_id}")
            except Exception as e:
                logger.error(f"Error sending escalation to {admin_id}: {e}")

    async def _send_call2_scheduled(self, lead: Dict, bot, call2_time: datetime):
        """Notify seller that Call #2 is scheduled."""
        from database import get_all_sellers

        seller_name = lead.get("Seller", "")
        sellers = await get_all_sellers()
        seller = next((s for s in sellers if s.get("full_name") == seller_name or s.get("username") == seller_name), None)

        if not seller:
            return

        telegram_id = seller["telegram_id"]
        lead_id = lead.get("ID", "")
        name = lead.get("Name", "")

        message = f"📅 <b>Qo'ng'iroq #2 Rejalashtirildi</b>\n\n"
        message += f"Lid ID: {lead_id}\n"
        message += f"Ism: {name}\n"
        message += f"Rejalashtirilgan vaqt: {format_datetime(call2_time)}\n\n"
        message += "Qo'ng'iroq #1 bajarildi. Qo'ng'iroq #2 2 soatdan keyin rejalashtirildi."

        try:
            await bot.send_message(telegram_id, message)
        except Exception as e:
            logger.error(f"Error sending Call #2 scheduled notification: {e}")

    async def _send_call2_reminder(self, lead: Dict, bot, reminder_key: str):
        """Send Call #2 reminder."""
        from database import get_all_sellers

        seller_name = lead.get("Seller", "")
        sellers = await get_all_sellers()
        seller = next((s for s in sellers if s.get("full_name") == seller_name or s.get("username") == seller_name), None)

        if not seller:
            return

        telegram_id = seller["telegram_id"]
        lead_id = lead.get("ID", "")
        name = lead.get("Name", "")
        phone = lead.get("Phone", "")

        message = f"⏰ <b>Eslatma: Qo'ng'iroq #2 Vaqti</b>\n\n"
        message += f"Lid ID: {lead_id}\n"
        message += f"Ism: {name}\n"
        message += f"Telefon: {phone}\n\n"
        message += "Qo'ng'iroq #2 vaqti keldi!"

        try:
            await bot.send_message(telegram_id, message)
        except Exception as e:
            logger.error(f"Error sending Call #2 reminder: {e}")

    async def _send_call3_scheduled(self, lead: Dict, bot, call3_time: datetime):
        """Notify seller that Call #3 is scheduled."""
        from database import get_all_sellers

        seller_name = lead.get("Seller", "")
        sellers = await get_all_sellers()
        seller = next((s for s in sellers if s.get("full_name") == seller_name or s.get("username") == seller_name), None)

        if not seller:
            return

        telegram_id = seller["telegram_id"]
        lead_id = lead.get("ID", "")
        name = lead.get("Name", "")

        message = f"📅 <b>Qo'ng'iroq #3 Rejalashtirildi</b>\n\n"
        message += f"Lid ID: {lead_id}\n"
        message += f"Ism: {name}\n"
        message += f"Rejalashtirilgan vaqt: {format_datetime(call3_time)}\n\n"
        message += "Qo'ng'iroq #2 bajarildi. Qo'ng'iroq #3 24 soatdan keyin rejalashtirildi."

        try:
            await bot.send_message(telegram_id, message)
        except Exception as e:
            logger.error(f"Error sending Call #3 scheduled notification: {e}")

    async def _send_call3_reminder(self, lead: Dict, bot, reminder_key: str):
        """Send Call #3 reminder."""
        from database import get_all_sellers

        seller_name = lead.get("Seller", "")
        sellers = await get_all_sellers()
        seller = next((s for s in sellers if s.get("full_name") == seller_name or s.get("username") == seller_name), None)

        if not seller:
            return

        telegram_id = seller["telegram_id"]
        lead_id = lead.get("ID", "")
        name = lead.get("Name", "")
        phone = lead.get("Phone", "")

        message = f"⏰ <b>Eslatma: Qo'ng'iroq #3 Vaqti</b>\n\n"
        message += f"Lid ID: {lead_id}\n"
        message += f"Ism: {name}\n"
        message += f"Telefon: {phone}\n\n"
        message += "Qo'ng'iroq #3 vaqti keldi!"

        try:
            await bot.send_message(telegram_id, message)
        except Exception as e:
            logger.error(f"Error sending Call #3 reminder: {e}")

    async def _send_first_class_reminder(self, lead: Dict, bot, time_str: str, reminder_key: str):
        """Send first class reminder."""
        from database import get_all_sellers

        seller_name = lead.get("Seller", "")
        sellers = await get_all_sellers()
        seller = next((s for s in sellers if s.get("full_name") == seller_name or s.get("username") == seller_name), None)

        if not seller:
            return

        telegram_id = seller["telegram_id"]
        lead_id = lead.get("ID", "")
        name = lead.get("Name", "")
        first_class_date = lead.get("First_Class_Date", "")

        message = f"📅 <b>Birinchi Dars Eslatmasi</b>\n\n"
        message += f"Lid ID: {lead_id}\n"
        message += f"Ism: {name}\n"
        message += f"Birinchi Dars: {first_class_date}\n"
        message += f"Qolgan vaqt: {time_str}\n\n"
        message += "Iltimos, qatnashishni tasdiqlang!"

        try:
            await bot.send_message(telegram_id, message)
        except Exception as e:
            logger.error(f"Error sending first class reminder: {e}")

    async def _send_did_not_attend_notification(self, lead: Dict, bot, reminder_key: str):
        """Send did not attend notification."""
        from database import get_all_sellers

        seller_name = lead.get("Seller", "")
        sellers = await get_all_sellers()
        seller = next((s for s in sellers if s.get("full_name") == seller_name or s.get("username") == seller_name), None)

        if not seller:
            return

        telegram_id = seller["telegram_id"]
        lead_id = lead.get("ID", "")
        name = lead.get("Name", "")

        message = f"⚠️ <b>Keyingi Qadam Kerak</b>\n\n"
        message += f"Lid ID: {lead_id}\n"
        message += f"Ism: {name}\n\n"
        message += "Lid birinchi darsga qatnashmadi. Iltimos, keyingi qadamni amalga oshiring!"

        try:
            await bot.send_message(telegram_id, message)
        except Exception as e:
            logger.error(f"Error sending did not attend notification: {e}")

