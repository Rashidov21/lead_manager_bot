"""
Main bot module - initializes the Telegram bot and sets up handlers.
"""
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from loguru import logger

from config import BOT_TOKEN, LOG_LEVEL, LOG_FILE
from handlers import admin, seller, common
from scheduler import SchedulerManager
from database import init_database


# Configure logging
logger.add(
    LOG_FILE,
    rotation="10 MB",
    retention="7 days",
    level=LOG_LEVEL,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
)


class LeadManagerBot:
    """Main bot class."""

    def __init__(self):
        self.bot = Bot(
            token=BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        self.dp = Dispatcher()
        self.scheduler = SchedulerManager(self.bot)

    async def setup_handlers(self):
        """Register all bot handlers."""
        # Common handlers (start, help)
        self.dp.message.register(common.start_handler, lambda m: m.text and m.text.startswith("/start"))
        self.dp.message.register(common.help_handler, lambda m: m.text and m.text.startswith("/help"))

        # Seller handlers
        self.dp.message.register(seller.mylids_handler, lambda m: m.text and m.text.startswith("/mylids"))
        self.dp.message.register(seller.pending_handler, lambda m: m.text and m.text.startswith("/pending"))
        self.dp.message.register(seller.update_status_handler, lambda m: m.text and m.text.startswith("/update_status"))
        self.dp.callback_query.register(seller.status_callback_handler)

        # Admin handlers
        self.dp.message.register(admin.dashboard_handler, lambda m: m.text and m.text.startswith("/dashboard"))
        self.dp.message.register(admin.allstats_handler, lambda m: m.text and m.text.startswith("/allstats"))
        self.dp.message.register(admin.sellerstats_handler, lambda m: m.text and m.text.startswith("/sellerstats"))
        self.dp.message.register(admin.lazy_handler, lambda m: m.text and m.text.startswith("/lazy"))
        self.dp.message.register(admin.settings_handler, lambda m: m.text and m.text.startswith("/settings"))

        logger.info("Bot handlers registered")

    async def start(self):
        """Start the bot."""
        try:
            # Initialize database
            await init_database()

            # Setup handlers
            await self.setup_handlers()

            # Start scheduler
            await self.scheduler.start()

            logger.info("Starting bot...")
            await self.dp.start_polling(self.bot, allowed_updates=self.dp.resolve_used_update_types())

        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise

    async def stop(self):
        """Stop the bot gracefully."""
        logger.info("Stopping bot...")
        await self.scheduler.stop()
        await self.bot.session.close()
        logger.info("Bot stopped")


# Global bot instance
bot_instance = None


async def get_bot() -> LeadManagerBot:
    """Get or create bot instance."""
    global bot_instance
    if bot_instance is None:
        bot_instance = LeadManagerBot()
    return bot_instance

