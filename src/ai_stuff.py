import tiktoken
from openai import AsyncOpenAI

from config import AI_EMOJI


def num_tokens_from_string(string: str, model: str = "gpt-3.5-turbo") -> int:
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = len(encoding.encode(string))
    return num_tokens


async def create_response(
    client: AsyncOpenAI, query: list[dict], img: str | None = None, model: str = "gpt-3.5-turbo"
) -> str:
    if img is not None:
        # Not possible due to changes in gpt4 format
        # I'll have to make a converter or something...
        """
        if model != "gpt-4-vision-preview":
            raise ValueError("Only \"gpt-4-vision-preview\" model can understand images")
        response = client.chat.completions.create(
            model=model,
            max_tokens=300,
            messages=[
                {"role": "system", "content": SYSTEM_MSG},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": img,
                            },
                        },
                    ],
                }
            ],
        )
        """
        raise NotImplementedError("Adding images isn't possible right now")
    else:
        response = await client.chat.completions.create(
            model=model,
            max_tokens=1000,
            messages=query,
        )

    return f"{AI_EMOJI} {response.choices[0].message.content}"


async def is_flagged(client: AsyncOpenAI, question: str) -> tuple:
    moderation = await client.moderations.create(input=question)
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
