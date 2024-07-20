import tiktoken
from loguru import logger
from openai import AsyncOpenAI

from base import Prompt
from constants import SEPARATOR_TOKEN, OPENROUTER_HEADERS


def num_tokens_from_string(string: str, model: str) -> int:
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = len(encoding.encode(string, disallowed_special=()))
    return num_tokens


async def create_response(
    client: AsyncOpenAI, prompt: Prompt, bot_id: str | int, model: str = "openai/gpt-3.5-turbo"
) -> str:
    logger.info(f"Selected model: {model}")
    bot_id = str(bot_id)
    rendered = prompt.full_render(bot_id)
    logger.info(rendered)
    response = await client.chat.completions.create(
        extra_headers=OPENROUTER_HEADERS,
        model=model,
        messages=rendered,
        max_tokens=1000,
        stop=[SEPARATOR_TOKEN],
    )
    if response.choices:
        return response.choices[0].message.content
