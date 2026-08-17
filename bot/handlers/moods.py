from aiogram import F, Router, types
from aiogram.filters import Command, CommandObject
from loguru import logger

from bot.core.config import settings
from bot.core.loader import dp
from bot.database.database import sessionmaker
from bot.database.models import MoodModel
from bot.keyboards import (
    choose_mood_generator,
    mood_page_generator,
)
from bot.services.generations import count_generations
from bot.services.moods import (
    add_mood,
    get_all_moods,
    get_mood,
    set_user_mood,
    update_mood_value,
)
from bot.services.users import user_exists
from bot.utils import moderate_query

router = Router(name="moods")


@dp.message(Command(commands=["moods", "муды"]))
async def list_mood_handler(message: types.Message):
    offset = 0
    async with sessionmaker() as session:
        moods = await get_all_moods(session, public_only=True, sort_by_popularity=True)

    if len(moods) == 0:
        await message.answer(
            f"{settings.emojis.system} Публичных мудов в боте пока не существует!"
        )
        return

    offset = max(offset, 0)

    new_moods = moods[offset : offset + 15]

    kbd = mood_page_generator(
        has_left=(offset > 0), has_right=(len(moods[offset + 15 :]) > 0), offset=offset
    )

    all_moods_str = ""
    for mood in new_moods:
        all_moods_str += f"\n• {mood[0].name} (id: {mood[0].id}){' - 👀 ' + str(mood[1]) if mood[1] > 0 else ''}"

    await message.answer(all_moods_str, reply_markup=kbd)


@dp.callback_query(F.data.startswith("moods/"))
async def list_mood_page_callback_handler(cb: types.CallbackQuery):
    # TODO: Repeated code from above
    if not cb.data:
        await cb.answer()
        return

    if not cb.message or isinstance(cb.message, types.InaccessibleMessage):
        await cb.answer()
        return

    try:
        offset: int = int(cb.data.split("/")[1])
    except ValueError:
        raise ValueError("Offset in callback is not an integer")

    async with sessionmaker() as session:
        moods = await get_all_moods(session, public_only=True, sort_by_popularity=True)

    if len(moods) == 0:
        await cb.message.edit_text(
            f"{settings.emojis.system} Публичных мудов в боте пока не существует, вы можете быть первым!"
        )
        await cb.answer()
        return

    offset = max(offset, 0)

    new_moods = moods[offset : offset + 15]

    kbd = mood_page_generator(
        has_left=(offset > 0), has_right=(len(moods[offset + 15 :]) > 0), offset=offset
    )

    all_moods_str = ""
    for mood in new_moods:
        all_moods_str += f"\n• {mood[0].name} (id: {mood[0].id}){' - 👀 ' + str(mood[1]) if mood[1] > 0 else ''}"

    await cb.message.edit_text(all_moods_str, reply_markup=kbd)


@dp.message(
    Command(commands=["setmood", "поменятьмуд", "установитьмуд", "выбратьмуд"])
)
async def set_mood_handler(message: types.Message, command: CommandObject):
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

        custom_mood = await get_mood(session, mood_id)
        if not custom_mood or (
            custom_mood.is_private is True
            and message.from_user.id != custom_mood.user_id
        ):
            await message.answer(f"{settings.emojis.system} Такого муда не существует!")
            return

        mood_id = custom_mood.id
        mood_name = custom_mood.name

        await set_user_mood(session, message.from_user.id, mood_id)

    await message.answer(
        f'{settings.emojis.system} Вы успешно выбрали муд "{mood_name}" (id: {mood_id})'
    )


@dp.callback_query(F.data.startswith("mood_id/"))
async def set_mood_callback_handler(cb: types.CallbackQuery):
    # TODO: Repeated code from above
    if not cb.data:
        await cb.answer()
        return

    if not cb.message or isinstance(cb.message, types.InaccessibleMessage):
        await cb.answer()
        return

    if not cb.message.from_user:
        await cb.answer()
        return

    try:
        mood_id: int = int(cb.data.split("/")[1])
    except ValueError:
        raise ValueError("Mood in callback is not an integer")

    async with sessionmaker() as session:
        if not (await user_exists(session, cb.message.from_user.id)):
            await cb.message.edit_text(
                f'{settings.emojis.system} Для этого нужен аккаунт! Создайте его командой "/начать"'
            )
            await cb.answer()
            return

        custom_mood = await get_mood(session, mood_id)
        if not custom_mood or (
            custom_mood.is_private is True
            and cb.message.from_user.id != custom_mood.user_id
        ):
            await cb.message.edit_text(
                f"{settings.emojis.system} Такого муда не существует!"
            )
            await cb.answer()
            return

        mood_id = custom_mood.id
        mood_name = custom_mood.name

        await set_user_mood(session, cb.message.from_user.id, mood_id)

    await cb.message.edit_text(
        f'{settings.emojis.system} Вы успешно выбрали муд "{mood_name}" (id: {mood_id})'
    )
    await cb.answer()


@dp.message(Command(commands=["createmood", "создатьмуд", "новыймуд"]))
async def create_mood_handler(message: types.Message, command: CommandObject):
    if not message.from_user:
        return

    if command.args is None:
        await message.answer(
            f"{settings.emojis.system} Чтобы создать новый муд,"
            f' напишите "/создатьмуд <инструкции>"'
            "\nИнструкции лучше всего писать на английском!"
            "\nНапример: You are now a cute anime girl. Don't forget to use :3 and other things"
            " that cute anime girls say. Speak only Russian."
        )
        return

    instr = command.args

    async with sessionmaker() as session:
        if not (await user_exists(session, message.from_user.id)):
            return (
                f"{settings.emojis.system} Гений, чтобы создать муд,"
                f' нужно сначала зарегаться командой "/начать".'
            )

        fail_reason = await moderate_query(instr)
        if fail_reason:
            return fail_reason

        user_moods = await get_all_moods(session, message.from_user.id)
        if len(user_moods) >= 10 and str(message.from_user.id) != settings.TG_ADMIN_ID:
            return f"{settings.emojis.system} Вы не можете создать больше 10 мудов!"

        # Creating mood
        inserted_id = await add_mood(
            session, message.from_user.id, "Мой муд", instr, False
        )

    # TODO: Make a keyboard for choosing a just created mood

    await message.answer(
        f"{settings.emojis.system} Вы создали новый муд! Его айди: {inserted_id}"
        "\nТеперь вы можете:"
        f'\n1. Поменять его название, с помощью команды "/муд имя {inserted_id} <название муда>".'
        "\n2. Поменять его описание, с помощью команды"
        f' "/муд описание {inserted_id} <описание муда>".'
        f'\n3. Сделать муд публичным, с помощью команды "/муд видимость {inserted_id}".'
        "\n4. Поменять его инструкции, если вам что-то не понравилось в них."
        f' Команда: "/муд инструкции {inserted_id} <инструкции>"'
    )


async def mood_info_handler(message: types.Message, mood_id: int):
    if not message.from_user:
        return

    async with sessionmaker() as session:
        mood = await get_mood(session, mood_id)

    is_admin = False
    if str(message.from_user.id) == settings.TG_ADMIN_ID:
        is_admin = True

    if not mood or (
        mood.is_private is True
        and mood.user_id != str(message.from_user.id)
        and not is_admin
    ):
        # If this mood doesn't exists or it's private...
        await message.answer(
            f"{settings.emojis.system} Айди с таким мудом не существует или он приватный!"
        )
        return

    async with sessionmaker() as session:
        generations = await count_generations(session, mood_id=mood.id)

    # ? I'm kinda stuck here. Telegram doesn't have an ability to just
    # ? get any user you want and their full name, unlike VK. In theory, we could create
    # ? a unique-to-telegram nickname system or... maybe something else?
    # ? I have no idea.

    msg = (
        f"{settings.emojis.system} Муд от пользователя - id: {mood.id}"
        f"\n👀 | Всего генераций: {generations}"
        f"\n👤 | Имя: {mood.name}"
        f"\n🗒 | Описание: {mood.description or '<Нету>'}"
        f"\n🤖 | Инструкции: {mood.instructions}"
    )
    choose_this_kbd = choose_mood_generator(mood.id)

    await message.answer(msg, reply_markup=choose_this_kbd)


async def handle_edit_mood(message: types.Message, params_str: str):
    if not message.from_user:
        return

    async with sessionmaker() as session:
        if not (await user_exists(session, message.from_user.id)):
            await message.answer(
                f"{settings.emojis.system} Что ты там менять собрался? У тебя даже аккаунта нет!"
                f'\n... Поэтому можешь его создать командой "/начать".'
            )
            return

        params = params_str.split()
        logger.info(f"Got these params: {params}")
        try:
            mood_id = int(params[1])
        except (KeyError, ValueError):
            await message.answer(
                f"{settings.emojis.system} Ты чет не то написал, броу!"
                "\nДоступные параметры: имя, описание, видимость"
            )
            return

        mood = await get_mood(session, mood_id)
        if not mood or mood.user_id != message.from_user.id:
            await message.answer(
                f"{settings.emojis.system} Гений, это не твой муд! Сделай его копию и меняй как хочешь."
            )
            return

        success_msg = ""
        if params[0] in ("имя", "название"):
            mood_name = " ".join(params[2:])
            fail_reason = await moderate_query(mood_name)
            if fail_reason:
                return fail_reason

            await update_mood_value(session, mood_id, MoodModel.name, mood_name)
            success_msg = "Вы успешно поменяли название муда!"
        elif params[0] == "описание":
            mood_desc = " ".join(params[2:])
            fail_reason = await moderate_query(mood_desc)
            if fail_reason:
                return fail_reason

            await update_mood_value(session, mood_id, MoodModel.description, mood_desc)
            success_msg = "Вы успешно поменяли описание муда!"
        elif params[0] == "видимость":
            visibility = mood.is_private

            new_is_private = True
            if visibility is True:
                new_is_private = False
            visibility_status = "приватный" if new_is_private else "публичный"

            await update_mood_value(
                session, mood_id, MoodModel.is_private, new_is_private
            )
            success_msg = f'Вы успешно поменяли видимость муда на "{visibility_status}"'
        elif params[0] == "инструкции":
            mood_instr = " ".join(params[2:])
            fail_reason = await moderate_query(mood_instr)
            if fail_reason:
                return fail_reason

            await update_mood_value(
                session, mood_id, MoodModel.instructions, mood_instr
            )
            success_msg = "Вы успешно поменяли инструкции муда!"
        else:
            await message.answer(
                f"{settings.emojis.system} Эээ... Что? Такого параметра нету, уж извини!"
            )
            return
    await message.answer(settings.emojis.system + " " + success_msg)


@dp.message(Command(commands=["mood", "муд"]))
async def mood_handler(message: types.Message, command: CommandObject):
    if command.args is None:
        # TODO: Return current mood if no args
        return

    is_info = False
    is_edit = False
    try:
        # Assuming command is mood info
        mood_id = int(command.args.split()[0])
        is_info = True
    except ValueError:
        # Assuming command is mood edit
        is_edit = True

    if is_info:
        await mood_info_handler(message, mood_id)
    elif is_edit:
        await handle_edit_mood(message, command.args)


@dp.message(Command(commands=["mymoods", "моимуды"]))
async def my_moods_handler(message: types.Message):
    if not message.from_user:
        return

    async with sessionmaker() as session:
        if not (await user_exists(session, message.from_user.id)):
            await message.answer(
                f"{settings.emojis.system} Гений, чтобы посмотреть свои муды,"
                f' нужно сначала зарегаться командой "/начать".'
            )
            return

        user_moods = await get_all_moods(session, message.from_user.id)
        if len(user_moods) == 0:
            await message.answer(
                f"{settings.emojis.system} Удивительно, но вы ещё не создавали собственный муд!"
                f'\nЧтобы его создать, напишите "/создатьмуд"'
            )
            return

        user_moods_message = f"{settings.emojis.system} Ваши муды:"
        for mood in user_moods:
            user_moods_message += f"\n• {mood.name} (id: {mood.id})"

    await message.answer(user_moods_message)
