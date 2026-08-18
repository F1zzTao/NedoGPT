from aiogram import Router, types
from aiogram.filters import Command, CommandObject

from bot.core.config import settings
from bot.core.loader import dp
from bot.database.database import sessionmaker
from bot.database.models import UserModel
from bot.services.moods import get_all_moods, get_mood, remove_mood
from bot.services.users import remove_user, update_user_value, user_exists

router = Router(name="delete_stuff")


@dp.message(Command(commands=["deletemood", "удалитьмуд"]))
async def del_mood_handler(message: types.Message, command: CommandObject):
    if not message.from_user:
        return

    if command.args is None:
        return

    try:
        mood_id = int(command.args)
    except ValueError:
        # ? Should we really return an error or maybe just ignore it?
        await message.answer(f"{settings.emojis.system} Укажите айди муда!")
        return

    async with sessionmaker() as session:
        if not (await user_exists(session, message.from_user.id)):
            await message.answer(
                f'{settings.emojis.system} Для этого нужен аккаунт! Создайте его командой "/начать"'
            )
            return

        mood = await get_mood(session, mood_id)
        if not mood or (
            mood.user_id != message.from_user.id
            and str(message.from_user.id) != settings.TG_ADMIN_ID
        ):
            await message.answer(
                f"{settings.emojis.system} Гений, это не твой муд. Если он тебя так раздражает,"
                " попроси его создателя удалить его."
            )
            return

        await remove_mood(session, mood_id)
    await message.answer(
        f"{settings.emojis.system} Ваш позорный муд удален и больше вас не позорит!"
    )


@dp.message(Command(commands=["deletepersona", "удалитьперсону"]))
async def del_persona_handler(message: types.Message):
    if not message.from_user:
        return

    async with sessionmaker() as session:
        if not (await user_exists(session, message.from_user.id)):
            await message.answer(f'{settings.emojis.system} Для этого нужен аккаунт! Создайте его командой "/начать"')
            return

        await update_user_value(session, message.from_user.id, UserModel.persona, "")
    await message.answer(f"{settings.emojis.system} Персона успешно удалена!")


@dp.message(Command(commands=["deletegpt", "удалитьгпт"]))
async def del_account_warning_handler(message: types.Message):
    if not message.from_user:
        return

    async with sessionmaker() as session:
        if not (await user_exists(session, message.from_user.id)):
            await message.answer(
                f"{settings.emojis.system} Пока мы живем в 2026, этот гений живет в 2027"
                '\nУ вас и так нет аккаунта. Отличная причина создать его командой "/начать"!'
            )
            return

        msg = f"{settings.emojis.system} Вы уверены, что хотите удалить свой аккаунт?"

        # ? Perhaps there's a better approach to handling account deletion when
        # ? user has created some moods?
        user_moods = await get_all_moods(session, message.from_user.id)
    if len(user_moods) > 0:
        msg += (
            f"\nВы создали муды ({len(user_moods)}). Удалив аккаунт, вы больше не"
            " сможете их редактировать, даже после создания нового аккаунта."
        )

    msg += '\nНапишите "/точноудалитьгпт" чтобы его удалить.'

    await message.answer(msg)


@dp.message(Command(commands=["deletegptsure", "точноудалитьгпт"]))
async def del_account_handler(message: types.Message):
    if not message.from_user:
        return

    async with sessionmaker() as session:
        if not (await user_exists(session, message.from_user.id)):
            await message.answer(f"{settings.emojis.system} Для этого нужен аккаунт!")
            return

        await remove_user(session, message.from_user.id)
    await message.answer(f"{settings.emojis.system} Готово... но зачем?")
