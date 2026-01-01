from telegrinder import (
    CallbackQuery,
    InlineButton,
    InlineKeyboard,
    Message,
    MessageCute,
)
from telegrinder.rules import CallbackDataEq, CallbackDataMarkup, Markup, Text
from telegrinder.types import User

from bot import handlers
from bot.base import UserInfo
from bot.core.config import settings
from bot.core.loader import dp
from bot.tg.keyboards_tg import OPEN_SETTINGS_KBD, SETTINGS_KBD

DEFAULT_PREFIX: str = "/"
tg_bot_id: str = "0"


def get_full_name(user: User):
    first_name = user.first_name
    last_name = user.last_name.unwrap_or("")
    if last_name:
        last_name = " " + last_name
    return first_name + last_name


@dp.message(Text(["/начать", "/start"]))
async def start_handler(message: Message):
    msg_reply = await handlers.handle_start(message.from_user.id, "tg")
    kbd = (OPEN_SETTINGS_KBD if msg_reply[1] else None)
    await message.answer(msg_reply[0], reply_markup=kbd)


@dp.message(Text(["/aihelp", "/help"]))
async def help_handler(_: Message):
    return handlers.handle_help()


@dp.message(Markup(["/ai <query>", "/gpt <query>"]))
async def ai_handler(message: Message, query: str):
    full_name = get_full_name(message.from_user)

    reply_user = None
    reply_query = None
    reply_message = message.reply_to_message.unwrap_or_none()
    if reply_message:
        reply_query = reply_message.text.unwrap_or_none()
        reply_full_name = get_full_name(reply_message.from_user)
        reply_user = UserInfo(reply_message.from_user.id, reply_full_name)

    user = UserInfo(message.from_user.id, full_name)

    wait_msg = await message.reply(f"{settings.emojis.system} Генерируем ответ, пожалуйста подождите...")
    msg_reply = await handlers.handle_ai(
        query, user, tg_bot_id, reply_user, reply_query
    )
    if isinstance(wait_msg, MessageCute):
        await wait_msg.edit(msg_reply)
    else:
        await message.reply(msg_reply)


@dp.message(Text(["/settings", "/гптнастройки"]))
async def settings_handler(message: Message):
    reply_message = message.reply_to_message.unwrap_or_none()
    msg_answer = await handlers.handle_settings(
        message.from_user.id, (reply_message.from_user.id if reply_message else None)
    )
    kbd = (SETTINGS_KBD if msg_answer[1] else None)
    await message.answer(msg_answer[0], reply_markup=kbd)


@dp.callback_query(CallbackDataEq("settings"))
async def settings_callback_handler(cb: CallbackQuery):
    msg_reply = await handlers.handle_settings(cb.from_user.id)
    kbd = (SETTINGS_KBD if msg_reply[1] else None)
    await cb.edit_text(msg_reply[0], reply_markup=kbd)


@dp.message(Text(["/moods", "/муды"]))
async def list_mood_handler(message: Message):
    result = await handlers.handle_mood_page(offset=0, platform="tg")

    if isinstance(result, str):
        # No keyboard
        await message.answer(result)
    else:
        # Page keyboard
        await message.answer(result[0], reply_markup=result[1])


@dp.callback_query(CallbackDataMarkup("moods/<offset:int>"))
async def list_mood_page_callback_handler(cb: CallbackQuery, offset: int):
    result = await handlers.handle_mood_page(offset=offset, platform="tg")

    if isinstance(result, str):
        # No keyboard
        await cb.edit_text(result)
    else:
        # Page keyboard
        await cb.edit_text(result[0], reply_markup=result[1])


@dp.message(Markup(["/mood <mood_id:int>", "/муд <mood_id:int>"]))
async def mood_info_handler(message: Message, mood_id: int):
    mood = await handlers.mood_exists(message.from_user.id, mood_id)
    if isinstance(mood, str):
        return mood

    # ? I'm kinda stuck here. Telegram doesn't have an ability to just
    # ? get any user you want and their full name, unlike VK. In theory, we could create
    # ? a unique-to-telegram nickname system or... maybe something else?
    # ? I have no idea.

    choose_this_kbd = (
        InlineKeyboard()
        .add(InlineButton(text="Выбрать этот муд", callback_data=f"mood_id/{mood.id}"))
    ).get_markup()

    mood_info_msg = await handlers.handle_mood_info(mood)
    await message.answer(mood_info_msg, reply_markup=choose_this_kbd)


@dp.message(
    Markup(
        [
            "/setmood <mood_id:int>",
            "/поменять муд <mood_id:int>",
            "/установить муд <mood_id:int>",
            "/выбрать муд <mood_id:int>"
        ]
    )
)
async def set_mood_handler(message: Message, mood_id: int):
    return (await handlers.handle_set_mood(message.from_user.id, mood_id))


@dp.callback_query(CallbackDataMarkup("mood_id/<mood_id:int>"))
async def set_mood_callback_handler(cb: CallbackQuery, mood_id: int):
    set_mood_msg = await handlers.handle_set_mood(cb.from_user.id, mood_id)
    await cb.edit_text(set_mood_msg)


@dp.message(Text(["/createmood", "/создать муд", "/новый муд"]))
async def create_mood_info_handler(_: Message):
    return handlers.handle_create_mood_info(DEFAULT_PREFIX)


@dp.message(Markup(["/создать муд <instr>", "/новый муд <instr>"]))
async def create_mood_handler(message: Message, instr: str):
    return (await handlers.handle_create_mood(
        message.from_user.id, instr, DEFAULT_PREFIX)
    )


@dp.message(Markup(["/mood <params_str>", "/муд <params_str>"]))
async def edit_mood_handler(message: Message, params_str: str):
    return (
        await handlers.handle_edit_mood(
            message.from_user.id, params_str, DEFAULT_PREFIX
        )
    )


@dp.message(Text(["/mymoods", "/мои муды"]))
async def my_moods_handler(message: Message):
    return (await handlers.handle_my_moods(message.from_user.id, DEFAULT_PREFIX))


@dp.message(Text(["/persona", "/персона"]))
async def persona_info_handler(_: Message):
    return handlers.handle_persona_info(DEFAULT_PREFIX)


@dp.message(Text(["/persona <persona>", "/персона <persona>"]))
async def persona_handler(message: Message, persona: str):
    return (await handlers.handle_set_persona(message.from_user.id, persona))


@dp.message(Text(["/mypersona", "/моя персона"]))
async def my_persona_handler(message: Message):
    return (await handlers.handle_my_persona(message.from_user.id))


@dp.message(Text(["/models", "/модели"]))
async def model_list_handler(_: Message):
    return (await handlers.handle_models_list(DEFAULT_PREFIX))


@dp.message(Markup(["/model <model_string>", "/модель <model_string>"]))
async def set_model_handler(message: Message, model_string: str):
    return (await handlers.handle_set_model(message.from_user.id, model_string))


@dp.message(Markup(["/deletemood <mood_id:int>", "/удалить муд <mood_id:int>"]))
async def del_mood_handler(message: Message, mood_id: int):
    return (await handlers.handle_del_mood(message.from_user.id, mood_id))


@dp.message(Text(["/deletepersona", "/удалить персону"]))
async def del_persona_handler(message: Message):
    return (await handlers.handle_del_persona(message.from_user.id))


@dp.message(Text(["/deletegpt", "/удалить гпт"]))
async def del_account_warning_handler(message: Message):
    return (await handlers.handle_del_account_warning(message.from_user.id))


@dp.callback_query(CallbackDataEq("delete_account"))
async def del_account_warning_callback_handler(cb: CallbackQuery):
    return (await handlers.handle_del_account_warning(cb.from_user.id))


@dp.message(Text(["/deletegptsure", "/точно удалить гпт"]))
async def del_account_handler(message: Message):
    return (await handlers.handle_del_account(message.from_user.id))
