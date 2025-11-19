"""
Common handlers for all users (start, help).
"""
from aiogram import types
from aiogram.filters import Command
from loguru import logger

from database import add_user, get_user_role, is_admin
from config import ROLE_ADMIN, ROLE_SELLER


async def start_handler(message: types.Message):
    """Handle /start command."""
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name

    # Add user to database (default role: seller)
    role = await get_user_role(user_id)
    if not role:
        # Check if user is in admin list (would be set via environment or manually)
        # For now, default to seller
        await add_user(user_id, username, full_name, ROLE_SELLER)
        role = ROLE_SELLER
    else:
        await add_user(user_id, username, full_name, role)

    welcome_text = f"👋 Xush kelibsiz, {full_name or username or 'Foydalanuvchi'}!\n\n"

    if role == ROLE_ADMIN:
        welcome_text += """<b>Admin Buyruqlari:</b>
/dashboard - Asosiy ko'rsatkichlar bilan boshqaruv paneli
/allstats - Barcha statistika
/sellerstats - Sotuvchilar ishlashi
/lazy - Kechiktirilgan vazifalar
/settings - Bot sozlamalari

<b>Sotuvchi Buyruqlari:</b>
/mylids - Sizning lidingiz
/pending - Kutilayotgan vazifalar
/update_status - Lid holatini yangilash
/help - Yordam"""
    else:
        welcome_text += """<b>Sotuvchi Buyruqlari:</b>
/mylids - Sizning lidingiz
/pending - Kutilayotgan vazifalar
/update_status - Lid holatini yangilash
/help - Yordam

Sizga avtomatik eslatmalar yuboriladi:
• Qo'ng'iroq #1, #2, #3
• Keyingi qadamlar
• Birinchi dars tasdiqlash"""

    await message.answer(welcome_text)
    logger.info(f"User {user_id} started the bot")


async def help_handler(message: types.Message):
    """Handle /help command."""
    user_id = message.from_user.id
    role = await get_user_role(user_id)

    if role == ROLE_ADMIN:
        help_text = """<b>Admin Yordami</b>

<b>Boshqaruv Paneli va Tahlil:</b>
/dashboard - Asosiy ko'rsatkichlar bilan umumiy ko'rinish
/allstats - To'liq statistika
/sellerstats - Har bir sotuvchi ishlashi
/lazy - Kechiktirilgan vazifalar bilan sotuvchilar

<b>Sotuvchi Buyruqlari:</b>
/mylids - Barcha lidingizni ko'rish
/pending - Amal qilish kerak bo'lgan vazifalarni ko'rish
/update_status - Lid holatini yangilash

<b>Qanday ishlaydi:</b>
• Lidlar Google Sheets'ga qo'shiladi
• Bot avtomatik eslatmalar yuboradi
• Boshqaruv paneli orqali ishlashni kuzatish"""
    else:
        help_text = """<b>Sotuvchi Yordami</b>

<b>Buyruqlar:</b>
/mylids - Barcha lidingizni ko'rish
/pending - Amal qilish kerak bo'lgan vazifalarni ko'rish
/update_status - Lid holatini yangilash

<b>Eslatmalar:</b>
Sizga avtomatik eslatmalar yuboriladi:
• Qo'ng'iroq #1 (1 soat, 2 soat, 12 soat eskalatsiya)
• Qo'ng'iroq #2 (Qo'ng'iroq #1 dan 2 soat keyin)
• Qo'ng'iroq #3 (Qo'ng'iroq #2 dan 24 soat keyin)
• Birinchi dars (24 soat va 2 soat oldin)
• Keyingi qadamlar

<b>Holatni yangilash:</b>
Lid holatini o'zgartirish uchun /update_status dan foydalaning.
Bot avtomatik ravishda keyingi qadamlarni rejalashtiradi."""

    await message.answer(help_text)

