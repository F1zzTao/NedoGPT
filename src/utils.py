import aiofiles
import msgspec
from openai import AsyncOpenAI
from vkbottle.bot import Message
from vkbottle_types.objects import (
    MessagesMessageAttachmentType,
    PhotosPhotoSizes
)

import ai_stuff
from config import BAN_WORDS, MAX_IMAGE_WIDTH, MOODS_PATH, SYSTEM_EMOJI


def pick_size(sizes: list[PhotosPhotoSizes]) -> str:
    sizes_widths = [photo.width for photo in sizes]
    filtered_sizes = [size for size in sizes_widths if size <= MAX_IMAGE_WIDTH]

    if not filtered_sizes:
        closest_size = min(sizes_widths, key=lambda x: abs(x - MAX_IMAGE_WIDTH))
    else:
        closest_size = max(filtered_sizes)

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


async def moderate_query(client: AsyncOpenAI, query: str) -> str | None:
    num_tokens = ai_stuff.num_tokens_from_string(query)
    if num_tokens > 4000:
        return (
            f"{SYSTEM_EMOJI} В сообщении более 4000"
            " токенов ({num_tokens})! Используйте меньше слов."
        )

    if any(ban_word in query.lower() for ban_word in BAN_WORDS):
        return f"{SYSTEM_EMOJI} Попробуй поговорить о чем-то другом. Поможет в развитии."

    try:
        flagged = await ai_stuff.is_flagged(client, query)
    except Exception as e:
        return f"{SYSTEM_EMOJI} Произошла ошибка во время модерации текста: {e}"

    if flagged[0] is True:
        return (
            f"{SYSTEM_EMOJI} Лил бро попытался забанить меня, но у него ничего не получилось :(\n"
            f"Запрос нарушает правила OpenAI: {flagged[1]}"
        )


async def get_moods() -> list[dict]:
    async with aiofiles.open(MOODS_PATH, "rb") as f:
        moods_list_bytes = await f.read()
    moods_list = msgspec.json.decode(moods_list_bytes)
    return moods_list


async def get_moods_desc() -> list[str]:
    moods_list = await get_moods()
    moods = [mood["desc"] for mood in moods_list]
    return moods


async def get_mood_by_id(mood_id: int) -> dict | None:
    moods_list = await get_moods()
    for mood in moods_list:
        if mood["id"] == mood_id:
            return mood
