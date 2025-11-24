import re

import aiohttp
from vkbottle.bot import Message
from vkbottle_types.objects import MessagesMessageAttachmentType, PhotosPhotoSizes

from bot import ai_stuff
from bot.core.config import OPENROUTER_HEADERS, Model, settings


def pick_size(sizes: list[PhotosPhotoSizes]) -> str | None:
    sizes_widths = [photo.width for photo in sizes]
    filtered_sizes = [size for size in sizes_widths if size <= settings.max_image_width]

    if not filtered_sizes:
        closest_size = min(sizes_widths, key=lambda x: abs(x - settings.max_image_width))
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
            f"{settings.emojis.system} В сообщении более 4000"
            f" токенов ({num_tokens})! Используйте меньше слов."
        )

    # Remove links
    query = re.sub(r'\.(?=[^\s])', '. ', query)


def censor_result(query: str) -> str:
    # Remove links
    query = re.sub(r'\.(?=[^\s])', '. ', query)

    for censor in settings.vk_censor_words:
        query = query.replace(censor, "***")
    return query


def find_model_by_id(models: list[Model], model_id: str) -> Model | None:
    for model in models:
        if model.id == model_id:
            return model


async def find_model_by_request(model_string: str) -> Model | None:
    async with aiohttp.ClientSession(headers=OPENROUTER_HEADERS) as session:
        async with session.get(settings.OPENAI_BASE_URL+"/models") as request:
            response = await request.json()

    for model in response["data"]:
        if model["id"] == model_string:
            new_model = Model(
                id=model["id"],
                name=model["id"],
                display_name=model["name"]
            )
            return new_model
