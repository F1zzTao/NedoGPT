import os

from dotenv import load_dotenv
from loguru import logger
from openai import AsyncOpenAI
from vkbottle import Keyboard, Text
from vkbottle import KeyboardButtonColor as Color
from vkbottle.bot import Bot
from vkbottle.bot import Message as VkMessage

import handlers
from base import ChatInfo, UserInfo
from keyboards_tg import SETTINGS_KBD
from keyboards_vk import OPEN_SETTINGS_KBD

load_dotenv()

VK_TOKEN = os.getenv("VK_API_KEY")
OPENAI_TOKEN = os.getenv("OPENAI_API_KEY")

bot = Bot(VK_TOKEN)
bot.labeler.vbml_ignore_case = True
client = AsyncOpenAI(api_key=OPENAI_TOKEN)


@bot.on.message(text=("начать", "!начать"))
async def start_handler(message: VkMessage):
    msg_reply = await handlers.handle_start(message.from_id)
    kbd = (OPEN_SETTINGS_KBD if msg_reply[1] else None)
    await message.answer(msg_reply[0], keyboard=kbd)


@bot.on.message(text=("!aihelp", "!команды"))
async def help_handler(_: VkMessage):
    return handlers.handle_help()


@bot.on.message(text=("!tokenize", "!tokenize <query>"))
async def count_tokens_handler(message: VkMessage, query: str | None = None):
    if message.reply_message:
        query = query or message.reply_message.text

    return handlers.handle_tokenize(query)


@bot.on.message(text=('!ai <query>', '!gpt3 <query>'))
async def ai_txt_handler(message: VkMessage, query: str):
    full_name = "Anonymous"
    bdate = "<unknown>"
    city_title = "<unknown>"
    sex = 0

    if message.from_id > 0:
        user = await message.get_user(fields=["bdate", "city", "sex"])
        full_name = user.first_name + " " + user.last_name
        bdate = user.bdate or bdate
        if user.city:
            city_title = user.city.title
        sex = user.sex

    user_info = UserInfo(message.from_id, full_name, bdate, city_title, sex)

    reply_user_info = None
    reply_query = None
    if message.reply_message:
        reply_query = message.reply_message.text
        if message.reply_message.from_id < 0:
            # Reply message is from group
            reply_full_name = "Anonymous"
        else:
            reply_user = await message.reply_message.get_user()
            reply_full_name = reply_user.first_name + " " + reply_user.last_name

        reply_user_info = UserInfo(message.reply_message.from_id, reply_full_name)

    chat_info_raw = (
        await bot.api.messages.get_conversations_by_id(peer_ids=[message.peer_id])
    ).items[0]
    chat_info = None
    if chat_info_raw.chat_settings:
        chat_info = ChatInfo(
            chat_info_raw.chat_settings.title, chat_info_raw.chat_settings.members_count
        )

    msg_reply = await handlers.handle_ai(
        client, query, user_info, reply_user_info, reply_query, chat_info
    )
    await message.reply(msg_reply)


@bot.on.message(text=("!гптнастройки", "!settings", "!настройки"))
@bot.on.message(payload={"cmd": "settings"})
async def open_settings_handler(message: VkMessage):
    msg_reply = handlers.handle_settings(message.from_id)
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
    if not mood_id:
        mood_id = payload["set_mood_id"]
    return (await handlers.handle_set_mood(message.from_id, mood_id))


@bot.on.message(text=("!создать муд", "!новый муд"))
async def create_mood_info_handler(_: VkMessage):
    return handlers.handle_create_mood_info()


@bot.on.message(text=("!создать муд <instr>", "!новый муд <instr>"))
async def create_mood_handler(message: VkMessage, instr: str | None = None):
    return (await handlers.handle_create_mood(client, message.from_id, instr))


@bot.on.message(text="!муд <params_str>")
async def edit_mood_handler(message: VkMessage, params_str: str):
    return (await handlers.handle_edit_mood(client, message.from_id, params_str))


@bot.on.message(text="!мои муды")
async def my_moods_handler(message: VkMessage):
    return (await handlers.handle_my_moods(message.from_id))


@bot.on.message(text="!удалить гпт")
@bot.on.message(payload={"cmd": "delete_account"})
async def del_account_handler(message: VkMessage):
    return (await handlers.handle_del_account(message.from_id))


if __name__ == "__main__":
    logger.info("Starting VK bot")
    bot.run_forever()
