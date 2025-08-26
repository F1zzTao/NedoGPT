from telegrinder import API as TgAPI
from telegrinder import Dispatch, Telegrinder, Token
from vkbottle import API as VkAPI
from vkbottle.bot import Bot

from constants import TG_TOKEN, VK_TOKEN

# VK
vk_api = VkAPI(VK_TOKEN)  # pyright: ignore
vk_bot = Bot(api=vk_api)

# Telegram
tg_api = TgAPI(token=Token(TG_TOKEN))  # pyright: ignore
tg_bot = Telegrinder(tg_api)
dp = Dispatch()