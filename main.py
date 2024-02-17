import time
import os

import tiktoken
from loguru import logger
from openai import OpenAI
from vkbottle.bot import Bot, Message
from dotenv import load_dotenv

load_dotenv()

bot = Bot(os.environ["VK_API_KEY"])
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
cooldown = 0

SYSTEM_MSG = "You are an assistant. Answer in russian language."


def num_tokens_from_string(string: str, model: str = "gpt-3.5-turbo") -> int:
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = len(encoding.encode(string))
    return num_tokens


@bot.on.message(text='!ai <question>')
async def ai_txt(message: Message, question: str):
    global cooldown
    if cooldown + 8 > time.time():
        return "КулДаун!"

    if message.reply_message is not None:
        question = f'[User answered to this message: "{message.reply_message}"] {question}'

    if num_tokens_from_string(question) > 100:
        return "В сообщении более 100 токенов! Используйте меньше слов."

    try:
        moderation = client.moderations.create(input=question)
        is_flagged = moderation.results[0].flagged
        moderation_dict = moderation.model_dump()
        categories_dict = moderation_dict['results'][0]['categories']
    except Exception as e:
        return f"Произошла ошибка во время модерации текста: {e}\n{moderation}"

    if is_flagged:
        flagged = []
        for category in categories_dict:
            is_flagged = categories_dict[category]
            if is_flagged:
                flagged.append(category)

        return (
            "Лил бро попытался забанить меня, но у него ничего не получилось :(\n"
            f"Запрос нарушает правила OpenAI: {', '.join(flagged)}"
        )

    cooldown = time.time()
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM_MSG},
                {"role": "user", "content": question}
            ]
        )
    except Exception as e:
        return f"Чет пошло не так: {e}"

    return response.choices[0].message.content


if __name__ == "__main__":
    logger.info("Starting bot...")
    bot.run_forever()
