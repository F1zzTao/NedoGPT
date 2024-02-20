import os
import re
import time

from dotenv import load_dotenv
from loguru import logger
from openai import OpenAI
from vkbottle.bot import Bot, Message
from vkbottle_types.objects import (
    MessagesMessageAttachmentType,
    PhotosPhotoSizes
)

import ai_stuff
from config import (
    AI_BAN_WORDS,
    AI_EMOJI,
    BAN_WORDS,
    CENSOR_WORDS,
    HELP_MSG,
    MAX_WIDTH,
    SYSTEM_EMOJI,
    SYSTEM_MSG
)

load_dotenv()

bot = Bot(os.environ["VK_API_KEY"])
group_id = os.environ["VK_GROUP_ID"]
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
cooldown = 0


def pick_size(sizes: list[PhotosPhotoSizes]) -> str:
    sizes_widths = [photo.width for photo in sizes]
    filtered_sizes = [size for size in sizes_widths if size <= MAX_WIDTH]

    if not filtered_sizes:
        closest_size = min(sizes_widths, key=lambda x: abs(x - MAX_WIDTH))
    else:
        closest_size = max(filtered_sizes)

    for photo in sizes:
        if photo.width == closest_size:
            photo_url = photo.url
            break

    return photo_url


def pick_img(message: Message) -> str | None:
    img_url = None
    if (
        message.attachments and
        message.attachments[0].type is MessagesMessageAttachmentType.PHOTO
    ):
        if message.from_id != 322615766:
            return f"{SYSTEM_EMOJI} Неа!"
        img_url = pick_size(message.attachments[0].photo.sizes)
    elif (
        message.reply_message and
        message.reply_message.attachments and
        message.reply_message.attachments[0].type is MessagesMessageAttachmentType.PHOTO
    ):
        if message.from_id != 322615766:
            return f"{SYSTEM_EMOJI} Неа!"
        img_url = pick_size(message.reply_message.attachments[0].photo.sizes)
    return img_url


async def process_query(message: Message, query_user: str) -> tuple[str, list[dict]]:
    """
    Returns a tuple of raw messages (for moderation) and messages
    """
    messages = [
        {"role": "system", "content": SYSTEM_MSG},
    ]

    if message.reply_message is not None:
        role = "user"
        reply_text = message.reply_message.text
        if str(message.reply_message.from_id) == "-"+group_id:
            reply_text = reply_text.replace(AI_EMOJI+" ", "")
            role = "assistant"
        reply_msg = {"role": role, "content": ""}

        try:
            reply_user = await bot.api.users.get(user_ids=message.reply_message.from_id)
            reply_msg["content"] = f"{reply_user[0].first_name} {reply_user[0].last_name}: "
        except Exception as e:
            logger.error(f"Couldn't add reply user name (group?): {e}")
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
    for message in messages:
        if message["role"] != "system":
            raw_messages += message["content"] + "\n"

    return (raw_messages, messages)


def moderate_query(client: OpenAI, query: str) -> str | None:
    num_tokens = ai_stuff.num_tokens_from_string(query)
    if num_tokens > 500:
        return (
            f"{SYSTEM_EMOJI} В сообщении более 500 токенов ({num_tokens})! Используйте меньше слов."
        )

    if any(ban_word in query.lower() for ban_word in BAN_WORDS):
        return f"{SYSTEM_EMOJI} Попробуй поговорить о чем-то другом. Поможет в развитии."

    try:
        flagged = ai_stuff.is_flagged(client, query)
    except Exception as e:
        return f"{SYSTEM_EMOJI} Произошла ошибка во время модерации текста: {e}"

    if flagged[0] is True:
        return (
            f"{SYSTEM_EMOJI} Лил бро попытался забанить меня, но у него ничего не получилось :(\n"
            f"Запрос нарушает правила OpenAI: {flagged[1]}"
        )


@bot.on.message(text="!aihelp")
async def ai_help(_: Message):
    return HELP_MSG


@bot.on.message(text=('!ai <query_user>', '!gpt3 <query_user>'))
async def ai_txt(message: Message, query_user: str):
    global cooldown
    if cooldown + 8 > time.time():
        return f"{SYSTEM_EMOJI} КулДаун!"

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


if __name__ == "__main__":
    logger.info("Starting bot...")
    bot.run_forever()
