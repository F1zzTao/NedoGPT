from loguru import logger

from bot.core.config import settings
from bot.core.loader import vk_bot
from bot.database.database import sessionmaker
from bot.services.moods import add_default_mood
from bot.vk import labeler


async def on_startup() -> None:
    async with sessionmaker() as session:
        result = await add_default_mood(session, int(settings.VK_ADMIN_ID))

    if result:
        logger.info("Successfully added the default mood")

if __name__ == "__main__":
    logger.add(
        "logs/vk_bot.log",
        level="DEBUG",
        format="{time} | {level} | {module}:{function}:{line} | {message}",
        rotation="100 KB",
        compression="zip",
    )

    logger.info("Starting VK bot")
    vk_bot.labeler.load(labeler)

    vk_bot.loop_wrapper.on_startup.append(on_startup())
    vk_bot.run_forever()