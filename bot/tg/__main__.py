from loguru import logger

from bot.core.config import settings
from bot.core.loader import tg_bot
from bot.database.database import sessionmaker
from bot.services.moods import add_default_mood
from bot.tg import dp


async def on_startup() -> None:
    global tg_bot_id
    bot_info = await tg_bot.api.get_me()
    tg_bot_id = str(bot_info.unwrap().id)

    async with sessionmaker() as session:
        result = await add_default_mood(session, int(settings.VK_ADMIN_ID))

    if result:
        logger.info("Successfully added the default mood")


if __name__ == "__main__":
    tg_bot.loop_wrapper.lifespan.on_startup(on_startup())
    tg_bot.on.load(dp)

    tg_bot.run_forever()