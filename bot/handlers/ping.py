from aiogram import Router, types
from aiogram.filters import Command

from bot.core.config import settings
from bot.core.loader import dp

router = Router(name="ping")


@dp.message(Command(commands=["ping", "пинг"]))
async def ping_handler(message: types.Message):
    await message.answer(f"{settings.emojis.system} Понг!")
