import re

from loguru import logger
from openai import AsyncOpenAI
from vkbottle.bot import Message
from vkbottle_types.objects import (
    MessagesMessageAttachmentType,
    PhotosPhotoSizes
)

import ai_stuff
from constants import (
    AI_BAN_WORDS,
    BAN_WORDS,
    CENSOR_WORDS,
    MAX_IMAGE_WIDTH,
    SYSTEM_BOT_PROMPT,
    SYSTEM_EMOJI,
    SYSTEM_USER_PROMPT
)
from db import get_value


def pick_size(sizes: list[PhotosPhotoSizes]) -> str:
    sizes_widths = [photo.width for photo in sizes]
    filtered_sizes = [size for size in sizes_widths if size <= MAX_IMAGE_WIDTH]

    if not filtered_sizes:
        closest_size = min(sizes_widths, key=lambda x: abs(x - MAX_IMAGE_WIDTH))
    else:
        closest_size = max(filtered_sizes)

    photo_url = ""
    for photo in sizes:
        if photo.width == closest_size:
            photo_url = photo.url
            break

    return photo_url


def pick_img(message: Message) -> str | None:
    img_url = None
    sizes = None
    if (
        message.attachments and
        message.attachments[0].type is MessagesMessageAttachmentType.PHOTO
    ):
        sizes = message.attachments[0].photo.sizes
    elif (
        message.reply_message and
        message.reply_message.attachments and
        message.reply_message.attachments[0].type is MessagesMessageAttachmentType.PHOTO
    ):
        sizes = message.reply_message.attachments[0].photo.sizes

    if sizes:
        img_url = pick_size(sizes)
    return img_url


async def process_instructions(
    instructions: str,
    user_id: int | None = None,
) -> str:
    new_instructions = instructions
    if user_id:
        user_persona = await get_value(user_id, "persona")
        if user_persona:
            new_instructions += '\n'+SYSTEM_USER_PROMPT.format(user_persona)
    new_instructions = SYSTEM_BOT_PROMPT.format(new_instructions)

    return new_instructions


async def moderate_query(query: str, client: AsyncOpenAI | None = None) -> str | None:
    num_tokens = ai_stuff.num_tokens_from_string(query)
    if num_tokens > 4000:
        return (
            f"{SYSTEM_EMOJI} В сообщении более 4000"
            f" токенов ({num_tokens})! Используйте меньше слов."
        )

    # Remove links
    query = re.sub(r'\.(?=[^\s])', '. ', query)

    if any(ban_word in query.lower() for ban_word in BAN_WORDS):
        return f"{SYSTEM_EMOJI} Попробуй поговорить о чем-то другом. Поможет в развитии."

    if client is not None:
        try:
            flagged = await ai_stuff.moderate(client, query)
        except Exception as e:
            logger.error(f"Couldn't moderate text: {e}")
            return f"{SYSTEM_EMOJI} Произошла ошибка во время модерации текста: {e}"

        if flagged[0] is True:
            return (
                f"{SYSTEM_EMOJI} Бан, бан, бан...\n"
                f"Запрос нарушает правила OpenAI: {flagged[1]}"
            )


def moderate_result(query: str) -> tuple[int, str]:
    # Remove links
    query = re.sub(r'\.(?=[^\s])', '. ', query)
    if (
        any(ban_word in query for ban_word in AI_BAN_WORDS)
    ):
        return (
            1,
            f"{SYSTEM_EMOJI} В результате оказалось слово из черного списка."
            " Спасибо, что потратил мои 0.0020 центов."
        )

    for censor in CENSOR_WORDS:
        query = query.replace(censor, "***")
    return (0, query)
