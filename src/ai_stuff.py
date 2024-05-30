import tiktoken
from loguru import logger
from openai import AsyncOpenAI

from base import Prompt
from constants import SEPARATOR_TOKEN


def num_tokens_from_string(string: str, model: str = "gpt-4o") -> int:
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = len(encoding.encode(string, disallowed_special=()))
    return num_tokens


async def create_response(
    client: AsyncOpenAI, prompt: Prompt, bot_id: str | int, model: str = "gpt-4o"
) -> str:
    logger.info(f"Selected model: {model}")
    bot_id = str(bot_id)
    rendered = prompt.full_render(bot_id)
    logger.info(rendered)
    response = await client.chat.completions.create(
        model=model,
        messages=rendered,
        max_tokens=1000,
        stop=[SEPARATOR_TOKEN],
    )
    return response.choices[0].message.content


async def moderate(client: AsyncOpenAI, query: str) -> tuple:
    moderation = await client.moderations.create(input=query)
    logger.info(f"Moderation results:\n{moderation}")
    is_flagged = moderation.results[0].flagged
    moderation_dict = moderation.model_dump()
    categories_dict = moderation_dict['results'][0]['categories']

    if is_flagged:
        flagged = []
        for category in categories_dict:
            is_flagged = categories_dict[category]
            if is_flagged:
                flagged.append(category)

        return (True, ', '.join(flagged))
    return (False, '')
