"""
Admin handlers for dashboard, statistics, and monitoring.
"""
from aiogram import types
from loguru import logger

from database import is_admin, add_seller_record
from services.kpi import KPIService
from google_sheets import sheets_client
from config import STATUS_CALL1_NEEDED
from utils.time_utils import parse_datetime, now_utc, hours_between


async def dashboard_handler(message: types.Message):
    """Handle /dashboard command - show admin dashboard."""
    user_id = message.from_user.id

    if not await is_admin(user_id):
        await message.answer("❌ Sizda bu buyruqni ishlatish uchun ruxsat yo'q.")
        return

    try:
        kpi_service = KPIService()
        dashboard_data = await kpi_service.get_dashboard()

        text = "<b>📊 Admin Boshqaruv Paneli</b>\n\n"

        # Overall metrics
        text += "<b>Umumiy Ko'rsatkichlar:</b>\n"
        text += f"Jami Lidlar: {dashboard_data.get('total_leads', 0)}\n"
        text += f"Faol Lidlar: {dashboard_data.get('active_leads', 0)}\n"
        text += f"Kechiktirilgan Lidlar: {dashboard_data.get('overdue_leads', 0)}\n"
        text += f"Bugungi Lidlar: {dashboard_data.get('leads_today', 0)}\n"
        text += f"Shu Hafta Lidlar: {dashboard_data.get('leads_this_week', 0)}\n\n"

        # Top sellers
        text += "<b>Eng Yaxshi Sotuvchilar (Shu Hafta):</b>\n"
        top_sellers = dashboard_data.get('top_sellers', [])[:5]
        for i, seller in enumerate(top_sellers, 1):
            text += f"{i}. {seller.get('name', 'N/A')}: {seller.get('leads', 0)} ta lid\n"

        # Recent alerts
        text += "\n<b>So'nggi Ogohlantirishlar:</b>\n"
        alerts = dashboard_data.get('recent_alerts', [])[:5]
        if alerts:
            for alert in alerts:
                text += f"⚠️ {alert}\n"
        else:
            text += "So'nggi ogohlantirishlar yo'q\n"

        await message.answer(text)

    except Exception as e:
        logger.error(f"Error in dashboard_handler: {e}")
        await message.answer("❌ Boshqaruv panelini yuklashda xatolik. Iltimos, keyinroq qayta urinib ko'ring.")


async def allstats_handler(message: types.Message):
    """Handle /allstats command - show all statistics."""
    user_id = message.from_user.id

    if not await is_admin(user_id):
        await message.answer("❌ Sizda bu buyruqni ishlatish uchun ruxsat yo'q.")
        return

    try:
        kpi_service = KPIService()
        stats = await kpi_service.get_all_stats()

        text = "<b>📈 Barcha Statistika</b>\n\n"

        # Overall conversion rates
        text += "<b>Umumiy Konversiya Darajalari:</b>\n"
        text += f"Qo'ng'iroq #1 Bajarilishi: {stats.get('call1_completion_rate', 0):.1f}%\n"
        text += f"Qo'ng'iroq #2 Bajarilishi: {stats.get('call2_completion_rate', 0):.1f}%\n"
        text += f"Qo'ng'iroq #3 Bajarilishi: {stats.get('call3_completion_rate', 0):.1f}%\n"
        text += f"Birinchi Dars Qatnashishi: {stats.get('first_class_attendance_rate', 0):.1f}%\n"
        text += f"Umumiy Konversiya: {stats.get('overall_conversion_rate', 0):.1f}%\n\n"

        # Lead sources
        text += "<b>Lid Manbalari:</b>\n"
        sources = stats.get('lead_sources', {})
        for source, count in list(sources.items())[:10]:
            text += f"{source}: {count}\n"

        # Daily stats
        text += "\n<b>Kunlik Statistika (Oxirgi 7 Kun):</b>\n"
        daily_stats = stats.get('daily_stats', [])
        for day_stat in daily_stats[-7:]:
            text += f"{day_stat.get('date', 'N/A')}: {day_stat.get('leads', 0)} ta lid\n"

        await message.answer(text)

    except Exception as e:
        logger.error(f"Error in allstats_handler: {e}")
        await message.answer("❌ Statistikalarni yuklashda xatolik. Iltimos, keyinroq qayta urinib ko'ring.")


async def sellerstats_handler(message: types.Message):
    """Handle /sellerstats command - show seller performance."""
    user_id = message.from_user.id

    if not await is_admin(user_id):
        await message.answer("❌ Sizda bu buyruqni ishlatish uchun ruxsat yo'q.")
        return

    try:
        kpi_service = KPIService()
        seller_stats = await kpi_service.get_seller_stats()

        text = "<b>👥 Sotuvchilar Ishlashi</b>\n\n"

        for seller_name, stats in seller_stats.items():
            text += f"<b>{seller_name}</b>\n"
            text += f"Jami Lidlar: {stats.get('total_leads', 0)}\n"
            text += f"Qo'ng'iroq #1: {stats.get('call1_completion_rate', 0):.1f}%\n"
            text += f"Qo'ng'iroq #2: {stats.get('call2_completion_rate', 0):.1f}%\n"
            text += f"Qo'ng'iroq #3: {stats.get('call3_completion_rate', 0):.1f}%\n"
            text += f"Birinchi Dars: {stats.get('first_class_attendance_rate', 0):.1f}%\n"
            text += f"Konversiya: {stats.get('conversion_rate', 0):.1f}%\n"
            text += "─" * 20 + "\n\n"

        if not seller_stats:
            text = "Sotuvchilar statistikasi mavjud emas."

        await message.answer(text)

    except Exception as e:
        logger.error(f"Error in sellerstats_handler: {e}")
        await message.answer("❌ Sotuvchilar statistikasini yuklashda xatolik. Iltimos, keyinroq qayta urinib ko'ring.")


async def lazy_handler(message: types.Message):
    """Handle /lazy command - show sellers with overdue tasks."""
    user_id = message.from_user.id

    if not await is_admin(user_id):
        await message.answer("❌ Sizda bu buyruqni ishlatish uchun ruxsat yo'q.")
        return

    try:
        leads = await sheets_client.get_all_leads()
        now = now_utc()

        # Group overdue leads by seller
        seller_overdue = {}

        for lead in leads:
            status = lead.get("Status", "")
            seller_name = lead.get("Seller", "")

            if not seller_name:
                continue

            is_overdue = False
            reason = ""

            if status == STATUS_CALL1_NEEDED:
                created_at_str = lead.get("Created_At", "")
                if created_at_str:
                    created_at = parse_datetime(created_at_str)
                    if created_at:
                        hours = hours_between(created_at, now)
                        if hours > 12:
                            is_overdue = True
                            reason = f"Qo'ng'iroq #1 kechikdi ({hours:.1f} soat)"

            if is_overdue:
                if seller_name not in seller_overdue:
                    seller_overdue[seller_name] = []
                seller_overdue[seller_name].append({
                    "lead_id": lead.get("ID", ""),
                    "name": lead.get("Name", ""),
                    "reason": reason
                })

        if not seller_overdue:
            await message.answer("✅ Kechiktirilgan vazifalar yo'q! Barcha sotuvchilar rejada.")
            return

        text = "<b>⚠️ Kechiktirilgan Vazifalar Bilan Sotuvchilar</b>\n\n"

        for seller_name, overdue_leads in seller_overdue.items():
            text += f"<b>{seller_name}</b> ({len(overdue_leads)} ta kechikdi)\n"
            for lead in overdue_leads[:5]:
                text += f"  • {lead['lead_id']} - {lead['name']}: {lead['reason']}\n"
            if len(overdue_leads) > 5:
                text += f"  ... va yana {len(overdue_leads) - 5} ta\n"
            text += "\n"

        await message.answer(text)

    except Exception as e:
        logger.error(f"Error in lazy_handler: {e}")
        await message.answer("❌ Kechiktirilgan vazifalarni yuklashda xatolik. Iltimos, keyinroq qayta urinib ko'ring.")


async def settings_handler(message: types.Message):
    """Handle /settings command - show bot settings."""
    user_id = message.from_user.id

    if not await is_admin(user_id):
        await message.answer("❌ Sizda bu buyruqni ishlatish uchun ruxsat yo'q.")
        return

    from config import (
        SHEET_POLL_INTERVAL,
        REMINDER_CALL1_1H,
        REMINDER_CALL1_2H,
        REMINDER_CALL1_12H,
        REMINDER_CALL2_DELAY,
        REMINDER_CALL3_DELAY,
    )

    text = "<b>⚙️ Bot Sozlamalari</b>\n\n"

    text += "<b>So'rov Konfiguratsiyasi:</b>\n"
    text += f"Jadval So'rov Oralig'i: {SHEET_POLL_INTERVAL} soniya\n\n"

    text += "<b>Eslatma Vaqtlari:</b>\n"
    text += f"Qo'ng'iroq #1 Eslatma 1: {REMINDER_CALL1_1H // 3600} soat\n"
    text += f"Qo'ng'iroq #1 Eslatma 2: {REMINDER_CALL1_2H // 3600} soat\n"
    text += f"Qo'ng'iroq #1 Eskalatsiya: {REMINDER_CALL1_12H // 3600} soat\n"
    text += f"Qo'ng'iroq #2 Kechikish: {REMINDER_CALL2_DELAY // 3600} soat\n"
    text += f"Qo'ng'iroq #3 Kechikish: {REMINDER_CALL3_DELAY // 3600} soat\n"

    text += "\n<i>Sozlamalarni o'zgartirish uchun config.py yoki environment o'zgaruvchilarini o'zgartiring.</i>"

    await message.answer(text)


async def add_seller_handler(message: types.Message):
    """Handle /add_seller command - admins can register sellers."""
    user_id = message.from_user.id

    if not await is_admin(user_id):
        await message.answer("❌ Sizda bu buyruqni ishlatish uchun ruxsat yo'q.")
        return

    # Parse: /add_seller <name> [telegram_id] or /add_seller <name> va <telegram_id>
    parts = message.text.split()
    
    if len(parts) < 2:
        await message.answer(
            "ℹ️ <b>Foydalanish:</b>\n\n"
            "<b>Variant 1:</b> /add_seller [Sotuvchi nomi]\n"
            "Masalan: /add_seller Ahmad\n\n"
            "<b>Variant 2:</b> /add_seller [Sotuvchi nomi] [telegram_id]\n"
            "Masalan: /add_seller Ahmad 1234567890\n\n"
            "<b>Variant 3:</b> /add_seller [Sotuvchi nomi] va [telegram_id]\n"
            "Masalan: /add_seller Ahmad va 1234567890"
        )
        return

    seller_name = parts[1].strip()
    if not seller_name:
        await message.answer("❌ Sotuvchi nomini kiriting.")
        return
    
    telegram_id = None

    # Check for "va" (and) separator or direct telegram_id
    if len(parts) >= 3:
        if len(parts) >= 4 and parts[2].lower() == "va":
            # Format: /add_seller name va telegram_id
            try:
                telegram_id = int(parts[3].strip())
            except (ValueError, IndexError):
                await message.answer("⚠️ Noto'g'ri Telegram ID format. Raqam bo'lishi kerak.")
                return
        else:
            # Format: /add_seller name telegram_id
            try:
                telegram_id = int(parts[2].strip())
            except ValueError:
                await message.answer("⚠️ Telegram ID raqam bo'lishi kerak.")
                return
    
    # Check if seller already exists
    from database import get_seller_by_name
    existing = await get_seller_by_name(seller_name)
    if existing:
        await message.answer(
            f"ℹ️ '{seller_name}' nomli sotuvchi allaqachon mavjud.\n\n"
            f"Telegram ID: {existing.get('telegram_id', 'Bog\'lanmagan')}\n"
            f"Holat: {'Faol' if existing.get('is_active') else 'Nofaol'}\n\n"
            f"Yangilash uchun /link_seller {seller_name} va [telegram_id] ishlating."
        )
        return

    await add_seller_record(seller_name, telegram_id=telegram_id)
    
    # Verify and get lead count
    from google_sheets import sheets_client
    leads = await sheets_client.get_leads_by_seller(seller_name)
    
    if telegram_id:
        await message.answer(
            f"✅ <b>{seller_name}</b> qo'shildi va Telegram ID {telegram_id} bilan bog'landi.\n\n"
            f"📋 Google Sheets'da {len(leads)} ta lid topildi.\n\n"
            f"✅ Sotuvchi endi botdan foydalanishi mumkin!"
        )
    else:
        await message.answer(
            f"✅ <b>{seller_name}</b> qo'shildi.\n\n"
            f"📋 Google Sheets'da {len(leads)} ta lid topildi.\n\n"
            f"Sotuvchi /link_seller {seller_name} buyrug'i orqali o'zini bog'lashi mumkin."
        )

