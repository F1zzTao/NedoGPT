from aiogram import Router, types
from aiogram.filters import CommandStart

from bot.core.config import settings
from bot.core.loader import dp
from bot.database.database import sessionmaker
from bot.keyboards import (
    OPEN_SETTINGS_KBD,
)
from bot.services.users import (
    add_user,
    user_exists,
)

DEFAULT_PREFIX: str = "/"
router = Router(name="start")


@dp.message(CommandStart())
async def start_handler(message: types.Message):
    if not message.from_user:
        await message.answer(
            f"{settings.emojis.system} Нет, ботёнок, для создания аккаунта ты должен быть человеком!"
        )
        return

    async with sessionmaker() as session:
        if await user_exists(session, message.from_user.id):
            # Person is already registered
            await message.answer(
                f"{settings.emojis.system} Гений, у тебя уже есть аккаунт в боте. Смирись с этим."
            )
            return

        await add_user(session, message.from_user.id)

    await message.answer(
        f"{settings.emojis.system} Аккаунт готов; теперь вы можете настраивать поведение бота!",
        reply_markup=OPEN_SETTINGS_KBD,
    )
