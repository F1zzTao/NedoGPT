from aiogram import F, Router, types
from aiogram.filters import Command
from loguru import logger

from bot.core.config import Model, settings
from bot.core.loader import dp
from bot.database.database import sessionmaker
from bot.keyboards import SETTINGS_KBD
from bot.services.moods import get_user_mood
from bot.services.users import get_user_model, user_exists

router = Router(name="settings")


@dp.message(Command(commands=["settings", "гптнастройки"]))
async def settings_handler(message: types.Message):
    reply_message = message.reply_to_message

    if not message.from_user:
        return

    user_id = str(message.from_user.id)

    admin_invoke = False
    if user_id == settings.TG_ADMIN_ID:
        admin_invoke = True

    is_reply_user = False
    if admin_invoke and reply_message and reply_message.from_user:
        user_id = reply_message.from_user.id
        is_reply_user = True

    async with sessionmaker() as session:
        if not (await user_exists(session, user_id)):
            if is_reply_user:
                await message.answer(
                    f'{settings.emojis.system} У этого юзера нету аккаунта! Создать он его может командой "/начать"'
                )
            else:
                await message.answer(
                    f'{settings.emojis.system} Для этого нужен аккаунт! Создайте его командой "/начать"'
                )
            return

        user_mood = await get_user_mood(session, user_id)
        logger.info(user_mood)
        if not user_mood:
            mood_id = 727727  # yup, that's osu! reference
            mood_name = "???"
            logger.warning(f"Couldnt' find {user_id}'s mood")
        else:
            mood_id = user_mood.id
            mood_name = user_mood.name

        user_model = await get_user_model(session, user_id)
    if not user_model:
        user_model = Model(id="0", name="???")

    if user_model.source == "bot":
        model_name = user_model.name
        if user_model.deprecation and user_model.deprecation.warning:
            model_name += " ⚠️"
    else:
        model_name = user_model.id

    current_model_string = (
        f"{user_model.display_name} ({model_name})"
        if user_model.display_name
        else model_name
    )

    msg = ""
    if is_reply_user:
        msg += (
            f"{settings.emojis.system} Информация об [id{user_id}|этом] пользователе:\n"
        )

    msg += (
        f"🎭 | Текущий муд: {mood_name} (id: {mood_id})\n"
        f"🤖 | Текущая модель: {current_model_string}"
    )

    await message.answer(msg, reply_markup=SETTINGS_KBD)


@dp.callback_query(F.data == "settings")
async def settings_callback_handler(cb: types.CallbackQuery):
    # TODO: Some repeated code from above (except reply user settings func)
    if not cb.message or isinstance(cb.message, types.InaccessibleMessage):
        await cb.answer()
        return

    if not cb.message.from_user:
        await cb.answer()
        return

    user_id = str(cb.message.from_user.id)

    async with sessionmaker() as session:
        if not (await user_exists(session, user_id)):
            await cb.message.edit_text(
                f'{settings.emojis.system} Для этого нужен аккаунт! Создайте его командой "/начать"'
            )
            await cb.answer()
            return

        user_mood = await get_user_mood(session, user_id)
        logger.info(user_mood)
        if not user_mood:
            mood_id = 727727  # yup, that's osu! reference
            mood_name = "???"
            logger.warning(f"Couldnt' find {user_id}'s mood")
        else:
            mood_id = user_mood.id
            mood_name = user_mood.name

        user_model = await get_user_model(session, user_id)
    if not user_model:
        user_model = Model(id="0", name="???")

    if user_model.source == "bot":
        model_name = user_model.name
        if user_model.deprecation and user_model.deprecation.warning:
            model_name += " ⚠️"
    else:
        model_name = user_model.id

    current_model_string = (
        f"{user_model.display_name} ({model_name})"
        if user_model.display_name
        else model_name
    )

    msg = (
        f"🎭 | Текущий муд: {mood_name} (id: {mood_id})\n"
        f"🤖 | Текущая модель: {current_model_string}"
    )

    await cb.message.edit_text(msg, reply_markup=SETTINGS_KBD)
    await cb.answer()
