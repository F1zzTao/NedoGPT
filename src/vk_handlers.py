from os import makedirs

from loguru import logger
from vkbottle import Keyboard, Text
from vkbottle import KeyboardButtonColor as Color
from vkbottle.bot import Bot
from vkbottle.bot import Message as VkMessage
from vkbottle_types.objects import UsersUserFull

import handlers
from base import UserInfo
from constants import SYSTEM_EMOJI, VK_ADMIN_ID, VK_BOT_ID, VK_TOKEN
from db import create_tables
from keyboards_vk import OPEN_SETTINGS_KBD, SETTINGS_KBD
from vk_middlewares import DonationMsgMiddleware

bot = Bot(VK_TOKEN)
bot.labeler.message_view.register_middleware(DonationMsgMiddleware)
bot.labeler.vbml_ignore_case = True  # pyright:ignore


@bot.on.message(text=("начать", "!начать"))
async def start_handler(message: VkMessage):
    msg_reply = await handlers.handle_start(message.from_id, "vk")
    kbd = (OPEN_SETTINGS_KBD if msg_reply[1] else None)
    await message.answer(msg_reply[0], keyboard=kbd)


@bot.on.message(text=("!aihelp", "!команды"))
async def help_handler(_: VkMessage):
    return handlers.handle_help()


@bot.on.message(text=('!ai <query>', '!gpt <query>', '.ai <query>'))
async def ai_txt_handler(message: VkMessage, query: str):
    full_name: str = "Anonymous"

    if message.from_id > 0:
        user = await message.get_user()
        if user.first_name and user.last_name:
            full_name = user.first_name + " " + user.last_name

    user_info = UserInfo(message.from_id, full_name)

    reply_user_info = None
    reply_query = None
    if message.reply_message:
        reply_query = message.reply_message.text
        reply_full_name = "Anonymous"
        if message.reply_message.from_id > 0:
            # Reply message is not from group
            reply_user = await message.reply_message.get_user()

            if isinstance(reply_user, UsersUserFull):
                if reply_user.first_name and reply_user.last_name:
                    reply_full_name = reply_user.first_name + " " + reply_user.last_name

        reply_user_info = UserInfo(message.reply_message.from_id, reply_full_name)

    wait_msg = await message.reply(f"{SYSTEM_EMOJI} Генерируем ответ, пожалуйста подождите...")
    msg_reply = await handlers.handle_ai(
        query, user_info, VK_BOT_ID, reply_user_info, reply_query
    )
    await message.ctx_api.messages.edit(
        peer_id=message.peer_id,
        cmid=wait_msg.conversation_message_id,
        message=msg_reply,
        keep_forward_messages=True,
    )


@bot.on.message(text=("!гптнастройки", "!settings", "!настройки"))
@bot.on.message(payload={"cmd": "settings"})
async def open_settings_handler(message: VkMessage):
    msg_reply = await handlers.handle_settings(message.from_id)
    kbd = (SETTINGS_KBD if msg_reply[1] else None)
    await message.answer(msg_reply[0], keyboard=kbd)


@bot.on.message(text=("!moods", "!муды"))
@bot.on.message(payload={"cmd": "change_gpt_mood_info"})
async def list_mood_handler(_: VkMessage):
    return (await handlers.handle_mood_list())


@bot.on.message(text="!муд <mood_id:int>")
async def custom_mood_info(message: VkMessage, mood_id: int):
    mood = await handlers.mood_exists(message.from_id, mood_id)
    if isinstance(mood, str):
        return mood

    creator_info = (await bot.api.users.get(user_ids=[mood[1]], name_case="gen"))[0]
    creator_full_name_gen = f"{creator_info.first_name} {creator_info.last_name}"

    choose_this_kbd = (
        Keyboard(inline=True)
        .add(Text("Выбрать этот муд", payload={"set_mood_id": mood[0]}), color=Color.PRIMARY)
    ).get_json()

    mood_info_msg = await handlers.handle_mood_info(mood, creator_full_name_gen)
    await message.answer(mood_info_msg, keyboard=choose_this_kbd, disable_mentions=True)


@bot.on.message(
    text=(
        "!setmood <mood_id:int>",
        "!поменять муд <mood_id:int>",
        "!установить муд <mood_id:int>",
        "!выбрать муд <mood_id:int>",
    )
)
@bot.on.message(payload_map=[("set_mood_id", int)])
async def change_mood_handler(message: VkMessage, mood_id: int | None = None):
    payload = message.get_payload_json()
    if isinstance(payload, dict) and mood_id is None:
        mood_id = payload["set_mood_id"]

    if isinstance(mood_id, int):
        return (await handlers.handle_set_mood(message.from_id, mood_id))


@bot.on.message(text=("!создать муд", "!новый муд"))
async def create_mood_info_handler(_: VkMessage):
    return handlers.handle_create_mood_info()


@bot.on.message(text=("!создать муд <instr>", "!новый муд <instr>"))
async def create_mood_handler(message: VkMessage, instr: str):
    return (await handlers.handle_create_mood(message.from_id, instr))


@bot.on.message(text="!муд <params_str>")
async def edit_mood_handler(message: VkMessage, params_str: str):
    return (await handlers.handle_edit_mood(message.from_id, params_str))


@bot.on.message(text="!мои муды")
async def my_moods_handler(message: VkMessage):
    return (await handlers.handle_my_moods(message.from_id))


@bot.on.message(text="!персона")
async def persona_info_handler(_: VkMessage):
    return handlers.handle_persona_info()


@bot.on.message(text="!персона <instr>")
async def set_persona_handler(message: VkMessage, instr: str):
    return (await handlers.handle_set_persona(message.from_id, instr))


@bot.on.message(text="!моя персона")
async def my_persona_handler(message: VkMessage):
    return (await handlers.handle_my_persona(message.from_id))


@bot.on.message(text="!модели")
async def model_list_handler(_: VkMessage):
    return (await handlers.handle_models_list())


@bot.on.message(text=("!модель <model_id_user:int>", "!выбрать модель <model_id_user:int>"))
async def set_model_handler(message: VkMessage, model_id_user: int):
    return (await handlers.handle_set_model(message.from_id, model_id_user))


@bot.on.message(text="!удалить муд <mood_id:int>")
async def del_mood_handler(message: VkMessage, mood_id: int):
    return (await handlers.handle_del_mood(message.from_id, mood_id))


@bot.on.message(text="!удалить персону")
async def del_persona_handler(message: VkMessage):
    return (await handlers.handle_del_persona(message.from_id))


@bot.on.message(text="!удалить гпт")
@bot.on.message(payload={"cmd": "delete_account"})
async def del_account_warning_handler(message: VkMessage):
    return (await handlers.handle_del_account_warning(message.from_id))


@bot.on.message(text="!точно удалить гпт")
async def del_account_handler(message: VkMessage):
    return (await handlers.handle_del_account(message.from_id))


@bot.on.message(text="!выдать суши <currency_str>")
async def admin_give_currency_handler(message: VkMessage, currency_str: str):
    if str(message.from_id) != VK_ADMIN_ID:
        return

    if not message.reply_message:
        return "Вы не указали ответ на сообщение."
    try:
        currency = int(currency_str)
    except ValueError:
        return "Вы указали неправильное количество валюты, укажите число."

    return (await handlers.handle_admin_give_currency(message.reply_message.from_id, currency))


if __name__ == "__main__":
    error_log_path = "errors"
    makedirs(error_log_path, exist_ok=True)
    logger.add(f"{error_log_path}/vk_log_{{time}}.log", level="WARNING", rotation="20 MB")

    logger.info("Starting VK bot")
    bot.loop_wrapper.on_startup.append(create_tables())
    bot.run_forever()
