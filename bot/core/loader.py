from redis.asyncio import ConnectionPool, Redis
from telegrinder import API as TgAPI
from telegrinder import Dispatch, Telegrinder, Token
from vkbottle import API as VkAPI
from vkbottle.bot import Bot

from bot.core.config import settings

# VK
vk_api = VkAPI(settings.VK_API_KEY)  # pyright: ignore
vk_bot = Bot(api=vk_api)

# Telegram
tg_api = TgAPI(token=Token(settings.TG_API_KEY))  # pyright: ignore
tg_bot = Telegrinder(tg_api)
dp = Dispatch()

redis_client = Redis(
    connection_pool=ConnectionPool(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASS,
        db=0,
    ),
)