from aiogram import Router, types
from aiogram.filters import Command, CommandObject

from bot.core.config import settings
from bot.core.loader import dp
from bot.database.database import sessionmaker
from bot.database.models import UserModel
from bot.services.users import get_user, update_user_value, user_exists
from bot.utils import moderate_query

router = Router(name="persona")


@dp.message(Command(commands=["persona", "персона"]))
async def persona_handler(message: types.Message, command: CommandObject):
    if not message.from_user:
        return

    if not command.args:
        await message.answer(
            f"{settings.emojis.system} Персону, как и инструкции, желательно писать на английском!"
            f"\nПример: /персона I'm Hu Tao. I work in Wangsheng Funeral Parlor"
            " together with Zhongli. I have very long brown twintail hair and flower-shaped"
            " pupils."
        )
        return

    persona = command.args

    async with sessionmaker() as session:
        if not (await user_exists(session, message.from_user.id)):
            await message.answer(
                f'{settings.emojis.system} Для этого нужен аккаунт! Создайте его командой "/начать"'
            )
            return

        fail_reason = await moderate_query(persona)
        if fail_reason:
            return fail_reason

        await update_user_value(
            session, message.from_user.id, UserModel.persona, persona
        )

    await message.answer(f"{settings.emojis.system} Вы успешно установили персону!")


@dp.message(Command(commands=["mypersona", "мояперсона"]))
async def my_persona_handler(message: types.Message):
    if not message.from_user:
        return

    async with sessionmaker() as session:
        user = await get_user(session, message.from_user.id)
        if not user:
            await message.answer(
                f'{settings.emojis.system} Для этого нужен аккаунт! Создайте его командой "/начать"'
            )
            return

    if user.persona:
        msg = f"{settings.emojis.system} Вот ваша персона: {user.persona}"
    else:
        msg = f"{settings.emojis.system} У вас ещё не установлена персона!"
    await message.answer(msg)
