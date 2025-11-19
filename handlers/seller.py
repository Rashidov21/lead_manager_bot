"""
Seller handlers for viewing leads, pending tasks, and updating status.
"""
import urllib.parse
from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from loguru import logger

from database import (
    is_seller,
    get_seller_by_telegram,
    get_seller_by_name,
    link_seller_to_telegram,
)
from google_sheets import sheets_client
from services.reminders import ReminderService
from services.kpi import KPIService
from config import (
    STATUS_CALL1_NEEDED,
    STATUS_CALL1_DONE,
    STATUS_CALL2_NEEDED,
    STATUS_CALL2_DONE,
    STATUS_CALL3_NEEDED,
    STATUS_CALL3_DONE,
    STATUS_FOLLOWUP_NEEDED,
    STATUS_FOLLOWUP_DONE,
    STATUS_FIRST_CLASS_SCHEDULED,
    STATUS_FIRST_CLASS_CONFIRMED,
    STATUS_NO_ANSWER,
    STATUS_COLD_LEAD,
    STATUS_LOST_LEAD,
    VALID_STATUSES,
)
from utils.time_utils import parse_datetime, format_datetime, now_utc, is_past


async def myleads_handler(message: types.Message):
    """Handle /myleads command - show seller's leads."""
    user_id = message.from_user.id

    if not await is_seller(user_id):
        await message.answer("❌ Sizda bu buyruqni ishlatish uchun ruxsat yo'q.")
        return

    seller_info = await get_seller_by_telegram(user_id)
    if not seller_info:
        await message.answer("❌ Sotuvchi ma'lumotlari topilmadi. Iltimos, admin bilan bog'laning.")
        return

    seller_name = seller_info.get("seller_name") or "Unknown"

    try:
        leads = await sheets_client.get_leads_by_seller(seller_name)

        if not leads:
            await message.answer("📋 Sizda hali hech qanday lid yo'q.")
            return

        # Format leads
        text = f"<b>📋 Sizning Lidingiz ({len(leads)})</b>\n\n"

        for lead in leads[:20]:  # Limit to 20 leads
            lead_id = lead.get("ID", "N/A")
            name = lead.get("Name", "N/A")
            status = lead.get("Status", "N/A")
            phone = lead.get("Phone", "N/A")
            created_at = lead.get("Created_At", "")

            text += f"<b>ID:</b> {lead_id}\n"
            text += f"<b>Ism:</b> {name}\n"
            text += f"<b>Telefon:</b> {phone}\n"
            text += f"<b>Holat:</b> {status}\n"
            if created_at:
                text += f"<b>Yaratilgan:</b> {created_at}\n"
            text += "─" * 20 + "\n\n"

        if len(leads) > 20:
            text += f"\n... va yana {len(leads) - 20} ta lid."

        await message.answer(text)

    except Exception as e:
        logger.error(f"Error in myleads_handler: {e}")
        await message.answer("❌ Lidalarni olishda xatolik. Iltimos, keyinroq qayta urinib ko'ring.")


async def pending_handler(message: types.Message):
    """Handle /pending command - show pending tasks."""
    user_id = message.from_user.id

    if not await is_seller(user_id):
        await message.answer("❌ Sizda bu buyruqni ishlatish uchun ruxsat yo'q.")
        return

    seller_info = await get_seller_by_telegram(user_id)
    if not seller_info:
        await message.answer("❌ Sotuvchi ma'lumotlari topilmadi. Iltimos, admin bilan bog'laning.")
        return

    seller_name = seller_info.get("seller_name") or "Unknown"

    try:
        leads = await sheets_client.get_leads_by_seller(seller_name)

        # Filter pending tasks
        pending = []
        for lead in leads:
            status = lead.get("Status", "")
            if status == STATUS_CALL1_NEEDED:
                pending.append(("Qo'ng'iroq #1 Kerak", lead))
            elif status in (STATUS_CALL1_DONE, STATUS_CALL2_NEEDED):
                call2_time = parse_datetime(lead.get("Call_2_Time", ""))
                if call2_time and is_past(call2_time):
                    pending.append(("Qo'ng'iroq #2 Vaqti", lead))
            elif status in (STATUS_CALL2_DONE, STATUS_CALL3_NEEDED):
                call3_time = parse_datetime(lead.get("Call_3_Time", ""))
                if call3_time and is_past(call3_time):
                    pending.append(("Qo'ng'iroq #3 Vaqti", lead))
            elif status == STATUS_FIRST_CLASS_SCHEDULED:
                pending.append(("1-dars Tasdiqlash Kerak", lead))
            elif status == STATUS_FOLLOWUP_NEEDED:
                pending.append(("Qayta aloqa vaqti", lead))

        if not pending:
            await message.answer("✅ Kutilayotgan vazifalar yo'q! Ajoyib ish!")
            return

        text = f"<b>⏰ Kutilayotgan Vazifalar ({len(pending)})</b>\n\n"

        for task_type, lead in pending[:15]:  # Limit to 15 tasks
            lead_id = lead.get("ID", "N/A")
            name = lead.get("Name", "N/A")
            phone = lead.get("Phone", "N/A")

            text += f"<b>{task_type}</b>\n"
            text += f"ID: {lead_id}\n"
            text += f"Ism: {name}\n"
            text += f"Telefon: {phone}\n"
            text += "─" * 20 + "\n\n"

        if len(pending) > 15:
            text += f"\n... va yana {len(pending) - 15} ta vazifa."

        await message.answer(text)

    except Exception as e:
        logger.error(f"Error in pending_handler: {e}")
        await message.answer("❌ Kutilayotgan vazifalarni olishda xatolik. Iltimos, keyinroq qayta urinib ko'ring.")


async def update_status_handler(message: types.Message):
    """Handle /update_status command - show status update interface."""
    user_id = message.from_user.id

    if not await is_seller(user_id):
        await message.answer("❌ Sizda bu buyruqni ishlatish uchun ruxsat yo'q.")
        return

    seller_info = await get_seller_by_telegram(user_id)
    if not seller_info:
        await message.answer("❌ Sotuvchi ma'lumotlari topilmadi. Iltimos, admin bilan bog'laning.")
        return

    seller_name = seller_info.get("seller_name") or "Unknown"

    try:
        leads = await sheets_client.get_leads_by_seller(seller_name)

        if not leads:
            await message.answer("📋 Yangilash uchun sizda hech qanday lid yo'q.")
            return

        # Show first 10 leads with status update buttons
        text = "<b>📝 Lid Holatini Yangilash</b>\n\nYangilash uchun lidni tanlang:\n\n"

        keyboard_buttons = []
        for lead in leads[:10]:
            lead_id = lead.get("ID", "N/A")
            name = lead.get("Name", "N/A")
            status = lead.get("Status", "N/A")
            text += f"<b>{lead_id}</b> - {name} ({status})\n"
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"{lead_id} - {name[:20]}",
                    callback_data=f"status_{lead_id}"
                )
            ])

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        await message.answer(text, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Error in update_status_handler: {e}")
        await message.answer("❌ Lidalarni yuklashda xatolik. Iltimos, keyinroq qayta urinib ko'ring.")


async def status_callback_handler(callback: types.CallbackQuery):
    """Handle status update callback."""
    user_id = callback.from_user.id

    if not await is_seller(user_id):
        await callback.answer("❌ Sizda ruxsat yo'q.", show_alert=True)
        return

    data = callback.data
    if not data or not data.startswith("status_"):
        await callback.answer("❌ Noto'g'ri amal.", show_alert=True)
        return

    # Check if this is a setstatus action
    if data.startswith("setstatus_"):
        await set_status_handler(callback)
        return

    lead_id = data.replace("status_", "")

    try:
        lead = await sheets_client.get_lead_by_id(lead_id)
        if not lead:
            await callback.answer("❌ Lid topilmadi.", show_alert=True)
            return

        current_status = lead.get("Status", "")

        # Create status selection keyboard
        keyboard_buttons = []
        for status in VALID_STATUSES:
            if status != current_status:
                # Encode status to avoid issues with special characters
                encoded_status = urllib.parse.quote(status, safe='')
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text=f"➡️ {status}",
                        callback_data=f"setstatus_{lead_id}_{encoded_status}"
                    )
                ])

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        text = f"<b>Lid {lead_id} Holatini Yangilash</b>\n\n"
        text += f"<b>Ism:</b> {lead.get('Name', 'N/A')}\n"
        text += f"<b>Joriy Holat:</b> {current_status}\n\n"
        text += "Yangi holatni tanlang:"

        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in status_callback_handler: {e}")
        await callback.answer("❌ Lidni yuklashda xatolik.", show_alert=True)


async def set_status_handler(callback: types.CallbackQuery):
    """Handle setting new status for a lead."""
    user_id = callback.from_user.id

    if not await is_seller(user_id):
        await callback.answer("❌ Sizda ruxsat yo'q.", show_alert=True)
        return

    data = callback.data
    if not data.startswith("setstatus_"):
        return

    # Extract lead_id and status from callback data
    # Format: setstatus_{lead_id}_{encoded_status}
    parts = data.replace("setstatus_", "", 1).split("_", 1)
    if len(parts) != 2:
        await callback.answer("❌ Noto'g'ri amal.", show_alert=True)
        return

    lead_id = parts[0]
    new_status = urllib.parse.unquote(parts[1])

    try:
        # Update status in Google Sheets
        success = await sheets_client.update_lead_status(lead_id, new_status)

        if success:
            # Trigger reminder service to handle status change
            from services.reminders import ReminderService
            reminder_service = ReminderService()
            await reminder_service.handle_status_change(lead_id, new_status)

            await callback.answer("✅ Holat muvaffaqiyatli yangilandi!")
            await callback.message.edit_text(
                f"✅ <b>Holat Yangilandi</b>\n\nLid {lead_id}\nYangi Holat: {new_status}"
            )
        else:
            await callback.answer("❌ Holatni yangilashda xatolik.", show_alert=True)

    except Exception as e:
        logger.error(f"Error in set_status_handler: {e}")
        await callback.answer("❌ Holatni yangilashda xatolik.", show_alert=True)


async def followup_handler(message: types.Message):
    """Handle /followup command to schedule follow-up."""
    user_id = message.from_user.id

    if not await is_seller(user_id):
        await message.answer("❌ Sizda bu buyruqni ishlatish uchun ruxsat yo'q.")
        return

    seller_info = await get_seller_by_telegram(user_id)
    if not seller_info:
        await message.answer("❌ Avval /link_seller orqali o'zingizni ro'yxatdan o'tkazing.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("ℹ️ Foydalanish: /followup <LID_ID> <YYYY-MM-DD HH:MM> | ixtiyoriy izoh")
        return

    payload = parts[1].strip()
    comment = ""
    if "|" in payload:
        schedule_text, comment = [chunk.strip() for chunk in payload.split("|", 1)]
    else:
        schedule_text = payload

    tokens = schedule_text.split()
    if len(tokens) < 2:
        await message.answer("❌ Sana va vaqtni ko'rsating. Masalan: /followup LID123 2025-01-10 14:00")
        return

    lead_id = tokens[0]
    datetime_str = " ".join(tokens[1:3]) if len(tokens) > 2 else tokens[1]
    followup_dt = parse_datetime(datetime_str)

    if not followup_dt:
        await message.answer("❌ Sana va vaqtni aniqlab bo'lmadi. Iltimos, YYYY-MM-DD HH:MM formatida kiriting.")
        return

    updates = {
        "Next_Followup": format_datetime(followup_dt),
        "Status": STATUS_FOLLOWUP_NEEDED,
    }
    if comment:
        updates["Comment"] = comment

    success = await sheets_client.update_lead(lead_id, updates)
    if success:
        await message.answer(
            f"✅ Qayta aloqa rejalashtirildi.\nLid: {lead_id}\nVaqt: {format_datetime(followup_dt)}"
        )
    else:
        await message.answer("❌ Lid topilmadi yoki yangilab bo'lmadi.")


async def kpi_handler(message: types.Message):
    """Handle /kpi command - show seller's KPI snapshot."""
    user_id = message.from_user.id

    if not await is_seller(user_id):
        await message.answer("❌ Sizda bu buyruqni ishlatish uchun ruxsat yo'q.")
        return

    seller_info = await get_seller_by_telegram(user_id)
    if not seller_info:
        await message.answer("❌ Avval /link_seller orqali o'zingizni ro'yxatdan o'tkazing.")
        return

    seller_name = seller_info.get("seller_name")
    kpi_service = KPIService()
    all_stats = await kpi_service.get_seller_stats()
    seller_stats = all_stats.get(seller_name)

    if not seller_stats:
        await message.answer("ℹ️ Siz uchun KPI ma'lumotlari mavjud emas.")
        return

    text = (
        f"<b>📊 {seller_name} KPI</b>\n\n"
        f"Jami lidlar: {seller_stats.get('total_leads', 0)}\n"
        f"Call #1 bajarilishi: {seller_stats.get('call1_completion_rate', 0):.1f}%\n"
        f"Call #2 bajarilishi: {seller_stats.get('call2_completion_rate', 0):.1f}%\n"
        f"Call #3 bajarilishi: {seller_stats.get('call3_completion_rate', 0):.1f}%\n"
        f"1-dars qatnashishi: {seller_stats.get('first_class_attendance_rate', 0):.1f}%\n"
        f"Konversiya: {seller_stats.get('conversion_rate', 0):.1f}%"
    )
    await message.answer(text)


async def link_seller_handler(message: types.Message):
    """Handle /link_seller command to attach Telegram user to seller name."""
    user_id = message.from_user.id

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("ℹ️ Foydalanish: /link_seller <Sotuvchi nomi>")
        return

    seller_name = parts[1].strip()
    if not seller_name:
        await message.answer("❌ Sotuvchi nomini kiriting.")
        return

    seller_record = await get_seller_by_name(seller_name)
    if not seller_record:
        await message.answer("❌ Bunday sotuvchi topilmadi. Admin /add_seller bilan qo'shishi kerak.")
        return

    await link_seller_to_telegram(seller_name, user_id)
    await message.answer(f"✅ {seller_name} profili Telegram hisobingizga bog'landi.")