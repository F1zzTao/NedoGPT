import aiohttp
import tiktoken
from loguru import logger

from constants import SEPARATOR_TOKEN


def num_tokens_from_string(string: str, model: str) -> int:
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = len(encoding.encode(string, disallowed_special=()))
    return num_tokens


async def create_response(
    headers: dict,
    url: str,
    messages: list[dict] | None = None,
    prompt: str | None = None,
    model: str = "openai/gpt-4o-mini",
) -> str | None:
    if (not messages and not prompt) or (messages and prompt):
        raise ValueError("Either `messages` or `prompt` must be provided")

    logger.info(f"Selected model: {model}")
    logger.info(messages or prompt)
    json_data = {
        "model": model,
        "max_tokens": 1000,
        "stop": [SEPARATOR_TOKEN],
    }
    if messages:
        json_data["messages"] = messages
    else:
        json_data["prompt"] = prompt

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(url+"/chat/completions", json=json_data) as request:
            response = await request.json()

    if response.get("choices"):
        choice = response["choices"][0]
        msg = choice.get("text") or choice["message"]["content"]
        return msg
