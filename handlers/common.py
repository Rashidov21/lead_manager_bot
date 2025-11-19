"""
Common handlers for all users (start, help).
"""
from aiogram import types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from loguru import logger

from database import add_user, get_user_role, is_admin
from config import ROLE_ADMIN, ROLE_SELLER


SELLER_MENU_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="/myleads"), KeyboardButton(text="/pending")],
        [KeyboardButton(text="/update_status"), KeyboardButton(text="/followup")],
        [KeyboardButton(text="/kpi"), KeyboardButton(text="/help")],
    ],
    resize_keyboard=True,
)


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
/myleads - Sizning lidingiz
/pending - Kutilayotgan vazifalar
/update_status - Lid holatini yangilash
/followup - Qayta aloqa rejalashtirish
/kpi - Shaxsiy KPI
/help - Yordam"""
    else:
        welcome_text += """<b>Sotuvchi Buyruqlari:</b>
/myleads - Sizning lidingiz
/pending - Kutilayotgan vazifalar
/update_status - Lid holatini yangilash
/followup - Qayta aloqa rejalashtirish
/kpi - Shaxsiy KPI
/help - Yordam

Sizga avtomatik eslatmalar yuboriladi:
• Qo'ng'iroq #1, #2, #3
• Keyingi qadamlar
• Birinchi dars tasdiqlash"""

    reply_markup = SELLER_MENU_KEYBOARD if role == ROLE_SELLER else None
    await message.answer(welcome_text, reply_markup=reply_markup)
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
/settings - Bot va eslatma sozlamalari
/add_seller <ism> [telegram_id] - yangi sotuvchini qo'shish

<b>Sotuvchi Buyruqlari:</b>
/myleads, /pending, /update_status, /followup, /kpi, /link_seller"""
        await message.answer(help_text)
    else:
        help_text = """<b>Sotuvchi Yordami</b>

<b>Asosiy tugmalar:</b>
/myleads - Barcha lidingizni ko'rish
/pending - Amal qilish kerak bo'lgan vazifalar
/update_status - Lid holatini yangilash
/followup - Qayta aloqa vaqtini belgilash
/kpi - Shaxsiy ko'rsatkichlar
/link_seller <ism> - Sotuvchi nomini Telegram bilan bog'lash

<b>Eslatmalar:</b>
• Qo'ng'iroq #1: 0/1/3/12 soatlik ogohlantirishlar
• Qo'ng'iroq #2: 2 soatdan keyin
• Qo'ng'iroq #3: 24 soatdan keyin
• Qayta aloqa va birinchi dars eslatmalari avtomatik yuboriladi.

<b>Holatni yangilash:</b>
/update_status orqali tanlang, bot jadvalni Google Sheets bilan sinxronlaydi."""

        await message.answer(help_text, reply_markup=SELLER_MENU_KEYBOARD)

