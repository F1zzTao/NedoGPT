import re

import aiohttp
from vkbottle.bot import Message
from vkbottle_types.objects import MessagesMessageAttachmentType, PhotosPhotoSizes

from bot import ai_stuff
from bot.constants import (
    CENSOR_WORDS,
    MAX_IMAGE_WIDTH,
    OPENAI_BASE_URL,
    OPENROUTER_HEADERS,
    SYSTEM_EMOJI,
)


def pick_size(sizes: list[PhotosPhotoSizes]) -> str | None:
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
        photo = message.attachments[0].photo
        if photo:
            sizes = photo.sizes
    elif (
        message.reply_message and
        message.reply_message.attachments and
        message.reply_message.attachments[0].type is MessagesMessageAttachmentType.PHOTO
    ):
        photo = message.reply_message.attachments[0].photo
        if photo:
            sizes = photo.sizes

    if sizes:
        img_url = pick_size(sizes)
    return img_url


async def process_main_prompt(
    system_prompt: str,
    persona_prompt: str,
    mood: str,
    persona: str | None,
) -> str:
    prompt = system_prompt.replace("{{description}}", mood)
    if persona:
        prompt = prompt+"\n\n"+persona_prompt.replace("{{persona}}", persona)

    return prompt


async def moderate_query(query: str) -> str | None:
    # We're counting gpt-4o tokens, however, models may be different.
    # Keep that in mind.
    num_tokens = ai_stuff.num_tokens_from_string(query, "gpt-4o")
    if num_tokens > 4000:
        return (
            f"{SYSTEM_EMOJI} В сообщении более 4000"
            f" токенов ({num_tokens})! Используйте меньше слов."
        )

    # Remove links
    query = re.sub(r'\.(?=[^\s])', '. ', query)


def censor_result(query: str) -> str:
    # Remove links
    query = re.sub(r'\.(?=[^\s])', '. ', query)

    for censor in CENSOR_WORDS:
        query = query.replace(censor, "***")
    return query


def find_model_by_id(models: list[dict], model_id: str) -> dict | None:
    for model in models:
        if str(model["id"]) == model_id:
            return model


async def find_model_by_request(model_string: str) -> dict | None:
    async with aiohttp.ClientSession(headers=OPENROUTER_HEADERS) as session:
        async with session.get(OPENAI_BASE_URL+"/models") as request:
            response = await request.json()

    for model in response["data"]:
        if model["id"] == model_string:
            return model
