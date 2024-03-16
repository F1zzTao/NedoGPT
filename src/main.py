import os
import re
import time

from dotenv import load_dotenv
from loguru import logger
from openai import OpenAI
from vkbottle import BaseMiddleware
from vkbottle.bot import Bot, Message

import ai_stuff
from config import AI_BAN_WORDS, AI_EMOJI, CENSOR_WORDS, HELP_MSG, SYSTEM_EMOJI
from db import (
    create_account,
    create_table,
    get_value,
    is_registered,
    update_value,
    delete_account
)
from keyboards import OPEN_SETTINGS_KBD, SETTINGS_KBD
from utils import (
    get_mood_by_id,
    get_moods,
    get_moods_desc,
    moderate_query,
    pick_img
)

load_dotenv()

bot = Bot(os.environ["VK_API_KEY"])
bot.labeler.vbml_ignore_case = True  # type: ignore
group_id = os.environ["VK_GROUP_ID"]
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
cooldown = 0

msg_history: dict = {}


class HistoryMiddleware(BaseMiddleware[Message]):
    async def pre(self):
        if not self.event.text:
            return

        query = await process_query(self.event, self.event.text, add_system=False)
        if msg_history.get(self.event.peer_id) is None:
            msg_history[self.event.peer_id] = [query[1][0]]
        else:
            msg_history[self.event.peer_id].append(query[1][0])


"""
class AccountMiddleware(BaseMiddleware[Message]):
    async def post(self):
        if not self.handlers:
            # User didn't use any commands
            return

        from_id = self.event.from_id
        peer_id = self.event.peer_id

        if from_id < 0:
            # Groups can't have an account
            return

        if (await is_registered(from_id, peer_id)):
            # Person is already registered
            return

        await create_account(from_id, peer_id)
"""


async def process_query(
    message: Message, query_user: str, add_system: bool = True
) -> tuple[str, list[dict]]:
    """
    Returns a tuple of raw messages (for moderation) and messages
    """
    if add_system:
        mood_id_str = await get_value(message.from_id, message.peer_id, "ai_mood")
        if mood_id_str is None:
            logger.info("User mood id not found, defaulting to normal")
            mood_id = 1
        else:
            mood_id = int(mood_id_str)

        selected_mood = await get_mood_by_id(mood_id)
        if selected_mood is None:
            raise ValueError(f"Unknown mood id: {mood_id}")

        messages = [
            {"role": "system", "content": selected_mood["instructions"]},
        ]
    else:
        messages = []

    if message.reply_message is not None:
        role = "user"
        reply_text = message.reply_message.text
        is_main_group = str(message.reply_message.from_id) == "-"+group_id
        if is_main_group:
            reply_text = reply_text.replace(AI_EMOJI+" ", "")
            role = "assistant"
        reply_msg = {"role": role, "content": ""}

        try:
            reply_user = await bot.api.users.get(user_ids=[message.reply_message.from_id])
            reply_msg["content"] = f"{reply_user[0].first_name} {reply_user[0].last_name}: "
        except Exception as e:
            logger.error(f"Couldn't add reply user name (group?): {e}")
            if not is_main_group:
                reply_msg["content"] = "[Anonymous]: "
        reply_msg["content"] += reply_text
        messages.append(reply_msg)

    new_msg = {"role": "user", "content": ""}
    try:
        user = await message.get_user()
        new_msg["content"] = f"{user.first_name} {user.last_name}: "
    except Exception as e:
        logger.error(f"Couldn't add user's name (group?): {e}")
        new_msg["content"] = "[Anonymous]: "
    new_msg["content"] += query_user
    messages.append(new_msg)

    raw_messages = ""
    for processed_message in messages:
        if processed_message["role"] != "system":
            raw_messages += processed_message["content"] + "\n"

    return (raw_messages, messages)


@bot.on.message(text="!aihelp")
async def ai_help_handler(_: Message):
    return HELP_MSG


@bot.on.message(text=("!tokenize", "!tokenize <query>"))
async def count_tokens_handler(message: Message, query: str | None = None):
    if query is None:
        if message.reply_message is None:
            return f"{SYSTEM_EMOJI} Эээ... А что токенизировать то?"
        num_tokens = ai_stuff.num_tokens_from_string(message.reply_message.text)
    else:
        num_tokens = ai_stuff.num_tokens_from_string(query)

    ending = ('' if num_tokens == 1 else 'а' if num_tokens < 5 else 'ов')
    cost = num_tokens/1000*0.0015
    cost_rounded = "{:.5f}".format(cost)
    return f"{SYSTEM_EMOJI} В сообщении {num_tokens} токен{ending} (${cost_rounded})!"


@bot.on.message(text=('!ai <query_user>', '!gpt3 <query_user>'))
async def ai_txt_handler(message: Message, query_user: str):
    global cooldown
    if cooldown + 8 > time.time():
        return f"{SYSTEM_EMOJI} Кул(ты)Даун!"

    if len(query_user) < 5:
        return f"{SYSTEM_EMOJI} В запросе должно быть больше 5 букв!"

    img_url = pick_img(message)
    query = await process_query(message, query_user)
    fail_reason = moderate_query(client, query[0])
    if fail_reason is not None:
        return fail_reason

    cooldown = time.time()
    try:
        if img_url is not None:
            if message.from_id != 322615766:
                return f"{SYSTEM_EMOJI} Неа!"
            # Not possible due to changes in gpt4 format
            # I'll have to make a converter or something...
            """
            ai_response = ai_stuff.create_response(
                client, query, img_url, "gpt-4-vision-preview"
            )
            """
            return f"{SYSTEM_EMOJI} Пока прикреплять картинки нельзя!"
        else:
            ai_response = ai_stuff.create_response(client, query[1])
    except Exception as e:
        return f"{SYSTEM_EMOJI} Чет пошло не так: {e}"

    logger.info(ai_response)

    if (
        any(ban_word in ai_response.lower() for ban_word in AI_BAN_WORDS) or
        re.search(r"[a-zA-Zа-яА-Я]\.[a-zA-Zа-яА-Я]", ai_response)
    ):
        return (
            f"{SYSTEM_EMOJI} В результате оказалось слово из черного списка."
            " Спасибо, что потратил мои 0.0020 центов."
        )

    for censor in CENSOR_WORDS:
        ai_response = ai_response.replace(censor, "***")

    return ai_response


@bot.on.message(text=("!aitldr <messages_num:int> <query_user>", "!aitldr <query_user>"))
async def ai_tldr_handler(message: Message, query_user: str, messages_num: int | None = None):
    global cooldown
    if cooldown + 8 > time.time():
        return f"{SYSTEM_EMOJI} Кул(ты)Даун!"

    messages_num = messages_num or 200
    if messages_num > 200:
        return f"{SYSTEM_EMOJI} Вы выбрали слишком много сообщений (макс. 200)!"

    if len(query_user) < 5:
        return f"{SYSTEM_EMOJI} В запросе должно быть больше 5 букв!"

    query = msg_history[message.peer_id][-messages_num:1].copy()

    history_text = ""
    for i in query:
        history_text += i["content"]+"\n"

    fail_reason = moderate_query(client, history_text)
    if fail_reason is not None:
        return fail_reason

    cooldown = time.time()
    try:
        ai_response = ai_stuff.create_response(client, query)
    except Exception as e:
        return f"{SYSTEM_EMOJI} Чет пошло не так: {e}"

    logger.info(ai_response)

    if (
        any(ban_word in ai_response.lower() for ban_word in AI_BAN_WORDS) or
        re.search(r"[a-zA-Zа-яА-Я]\.[a-zA-Zа-яА-Я]", ai_response)
    ):
        return (
            f"{SYSTEM_EMOJI} В результате оказалось слово из черного списка."
            " Спасибо, что потратил мои 0.002 центов."
        )

    for censor in CENSOR_WORDS:
        ai_response = ai_response.replace(censor, "***")

    return ai_response


@bot.on.message(text=("начать", "!начать"))
async def start_handler(message: Message):
    if message.from_id < 0:
        # Groups can't have an account
        return f"{SYSTEM_EMOJI} Нет, ботёнок, для создания аккаунта ты должен быть человеком!"

    if (await is_registered(message.from_id, message.peer_id)):
        # Person is already registered
        return f"{SYSTEM_EMOJI} Гений, у тебя уже есть аккаунт в боте. Смирись с этим."

    await create_account(message.from_id, message.peer_id)
    await message.answer(
        f"{SYSTEM_EMOJI} Аккаунт готов; теперь вы можете настраивать поведение бота!",
        keyboard=OPEN_SETTINGS_KBD
    )


@bot.on.message(text="!гптнастройки")
@bot.on.message(payload={"cmd": "settings"})
async def open_settings_handler(message: Message):
    if not (await is_registered(message.from_id, message.peer_id)):
        return f"{SYSTEM_EMOJI} Для этого надо зарегестрироваться!"
    await message.answer("Держи настройки!", keyboard=SETTINGS_KBD)


@bot.on.message(text="!поменять настроение")
@bot.on.message(payload={"cmd": "change_gpt_mood"})
async def list_mood_handler(_: Message):
    moods = await get_moods_desc()
    moods_str = "На данный момент боту можно задать такие настроения:\n"
    for i, mood in enumerate(moods, 1):
        moods_str += f"{i}. {mood}\n"
    moods_str += "\nЧтобы задать настроение боту, напишите \"!поменять настроение <номер>\"."
    return moods_str


@bot.on.message(text="!поменять настроение <mood_num:int>")
async def change_mood_handler(message: Message, mood_num: int):
    if not (await is_registered(message.from_id, message.peer_id)):
        return (
            f"{SYSTEM_EMOJI} Гений, чтобы поменять настроение,"
            " нужно зарегаться командой \"!начать\"."
        )

    moods = await get_moods()
    selected_mood = None
    for mood in moods:
        if mood["id"] == mood_num:
            selected_mood = mood
            break

    if selected_mood is None:
        return (
            f"{SYSTEM_EMOJI} Гений, вообще-то настроение надо выбирать"
            " из списка, который можно узнать, написав просто \"!поменять настроение\"."
        )

    await update_value(message.from_id, message.peer_id, "ai_mood", selected_mood["id"])
    return f"{SYSTEM_EMOJI} Вы выбрали настроение: {selected_mood['name']}."


@bot.on.message(text="!удалить гпт")
@bot.on.message(payload={"cmd": "delete_account"})
async def delete_account_handler(message: Message):
    if not (await is_registered(message.from_id, message.peer_id)):
        return (
            f"{SYSTEM_EMOJI} Пока мы живем в 2024, этот гений живет в 1488"
            "\nУ вас и так нет аккаунта. Отличная причина создать такой!"
        )
    await delete_account(message.from_id, message.peer_id)
    return f"{SYSTEM_EMOJI} Готово... но зачем?"


if __name__ == "__main__":
    logger.info("Starting bot...")
    bot.loop_wrapper.on_startup.append(create_table())
    bot.labeler.message_view.register_middleware(HistoryMiddleware)
    bot.run_forever()
