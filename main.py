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

SYSTEM_MSG = "You are an assistant. Answer in user's language."


def num_tokens_from_string(string: str, model: str = "gpt-3.5-turbo") -> int:
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = len(encoding.encode(string))
    return num_tokens


def create_response(question: str, model: str = "gpt-3.5-turbo") -> str:
    response = client.chat.completions.create(
        model=model,
        max_tokens=1000,
        messages=[
            {"role": "system", "content": SYSTEM_MSG},
            {"role": "user", "content": question}
        ]
    )

    return response.choices[0].message.content


def is_flagged(question: str) -> tuple:
    moderation = client.moderations.create(input=question)
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


@bot.on.message(text=('!ai <question_user>', '!gpt3 <question_user>'))
async def ai_txt(message: Message, question_user: str):
    global cooldown
    if cooldown + 8 > time.time():
        return "КулДаун!"

    try:
        user = await message.get_user()
        question = f"[User's full name: \"{user.first_name} {user.last_name}\"] "
    except Exception as e:
        logger.error(f"Couldn't add user's name (group?): {e}")
        question = ""

    if message.reply_message is not None:
        try:
            reply_user = await bot.api.users.get(user_ids=message.reply_message.from_id)
            full_name = f' (Reply user full name: "{reply_user[0].first_name} {reply_user[0].last_name}")'
        except Exception as e:
            logger.error(f"Couldn't add reply user's name (group?): {e}")
            full_name = ""
        question += f'[User answered to this message{full_name}: "{message.reply_message.text}"] '

    question += question_user
    num_tokens = num_tokens_from_string(question)
    if num_tokens > 500:
        return f"В сообщении более 500 токенов ({num_tokens})! Используйте меньше слов."

    try:
        flagged = is_flagged(question)
    except Exception as e:
        return f"Произошла ошибка во время модерации текста: {e}"

    if flagged[0] is True:
        return (
            "Лил бро попытался забанить меня, но у него ничего не получилось :(\n"
            f"Запрос нарушает правила OpenAI: {flagged[1]}"
        )

    cooldown = time.time()
    try:
        ai_response = create_response(question)
    except Exception as e:
        return f"Чет пошло не так: {e}"

    return ai_response


if __name__ == "__main__":
    logger.info("Starting bot...")
    bot.run_forever()
