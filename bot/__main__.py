import asyncio

from loguru import logger

from bot.core.loader import bot, dp
from bot.handlers import get_handlers_router


async def on_startup() -> None:
    dp.include_router(get_handlers_router())
    logger.info("Bot started")


async def on_shutdown() -> None:
    logger.info("Bot stopped")


async def main() -> None:
    logger.add(
        "logs/telegram_bot.log",
        level="DEBUG",
        format="{time} | {level} | {module}:{function}:{line} | {message}",
        rotation="100 KB",
        compression="zip",
    )

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())