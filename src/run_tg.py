from core.loader import tg_bot
from db import create_tables
from tg import dp
from tg.tg_middlewares import DatabaseMiddleware


async def set_bot_id():
    global tg_bot_id
    bot_info = await tg_bot.api.get_me()
    tg_bot_id = str(bot_info.unwrap().id)


if __name__ == "__main__":
    tg_bot.loop_wrapper.lifespan.on_startup(create_tables())
    tg_bot.loop_wrapper.lifespan.on_startup(set_bot_id())
    tg_bot.on.load(dp)
    tg_bot.on.message.register_middleware(DatabaseMiddleware())

    tg_bot.run_forever()