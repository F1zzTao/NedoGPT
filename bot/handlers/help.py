from aiogram import Router, types
from aiogram.filters import Command

from bot.core.config import HELP_MSG
from bot.core.loader import dp

router = Router(name="help")

@dp.message(Command(commands=["help", "aihelp"]))
async def help_handler(message: types.Message):
    await message.answer(HELP_MSG)
