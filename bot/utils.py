import re
from typing import Literal, overload

import aiohttp

from bot import ai_stuff
from bot.cache.redis import cached
from bot.core.config import OPENROUTER_HEADERS, Model, settings


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

    for censor in settings.censor_words:
        query = query.replace(censor, "***")
    return query


def find_model_by_id(models: list[Model], model_id: str) -> Model | None:
    for model in models:
        if model.id == model_id:
            return model


@cached(ttl=1800)
async def get_model_list() -> dict:
    async with aiohttp.ClientSession(headers=OPENROUTER_HEADERS) as session:  # noqa: SIM117
        async with session.get(settings.OPENAI_BASE_URL+"/models") as request:
            response = await request.json()
    return response["data"]

@overload
async def find_model_by_request(model_string: str, raw: Literal[True]) -> dict | None: ...
@overload
async def find_model_by_request(model_string: str, raw: Literal[False]) -> Model | None: ...
@overload
async def find_model_by_request(model_string: str) -> Model | None: ...

async def find_model_by_request(model_string: str, raw: bool = False) -> Model | dict | None:
    models = await get_model_list()

    for model in models:
        if model["id"] == model_string:
            if raw:
                return model
            new_model = Model(
                id=model["id"],
                name=model["id"],
                display_name=model["name"]
            )
            return new_model


async def is_model_free(model_string: str) -> bool | dict | None:
    model = await find_model_by_request(model_string, raw=True)
    if not model:
        return

    pricing = model.get("pricing")
    if not pricing:
        return

    if any(pricing[_type] != "0" for _type in pricing):
        return pricing

    return True
