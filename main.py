"""
Main entry point for the Lead Manager Bot.
"""
import asyncio
import signal
import sys
from loguru import logger

from bot import LeadManagerBot


async def main():
    """Main function to run the bot."""
    bot = None

    try:
        bot = LeadManagerBot()
        logger.info("Initializing bot...")

        # Setup signal handlers for graceful shutdown
        def signal_handler(sig, frame):
            logger.info("Received shutdown signal")
            if bot:
                asyncio.create_task(bot.stop())
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Start the bot
        await bot.start()

    except KeyboardInterrupt:
        logger.info("Bot interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
    finally:
        if bot:
            await bot.stop()
        logger.info("Bot shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

