import tiktoken
from openai import AsyncOpenAI

from constants import BOT_ID, SEPARATOR_TOKEN
from base import Prompt


def num_tokens_from_string(string: str, model: str = "gpt-3.5-turbo") -> int:
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = len(encoding.encode(string))
    return num_tokens


async def create_response(
    client: AsyncOpenAI, prompt: Prompt, model: str = "gpt-3.5-turbo"
) -> str:
    rendered = prompt.full_render(BOT_ID)
    response = await client.chat.completions.create(
        model=model,
        messages=rendered,
        max_tokens=1000,
        stop=[SEPARATOR_TOKEN],
    )
    return response.choices[0].message.content


async def moderate(client: AsyncOpenAI, query: str) -> tuple:
    moderation = await client.moderations.create(input=query)
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
