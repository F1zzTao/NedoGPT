from aiogram import Router, types
from aiogram.filters import Command

from bot.core.config import settings
from bot.core.loader import dp

router = Router(name="help")

# TODO: i18n
HELP_MSG: str = (
    f"{settings.emojis.system} Вот все популярные команды:"
    "\n/ai <текст> - отвечает на ваш запрос, используя ваш выбранный муд"
    " (по умолчанию используется обычный ассистент)"
    "\n/mood <имя|описание|инструкции|видимость> [значение] - устанавливает"
    " параметры для вашего муда"
    f"\nВсе остальные команды вы можете найти в репозитории бота: {settings.links.bot_help_link}"
)

@dp.message(Command(commands=["help", "aihelp"]))
async def help_handler(message: types.Message):
    await message.answer(HELP_MSG)
