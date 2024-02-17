import time
import os

import tiktoken
from loguru import logger
from openai import OpenAI
from vkbottle.bot import Bot, Message
from dotenv import load_dotenv
from vkbottle_types.objects import MessagesMessageAttachmentType, PhotosPhotoSizes

load_dotenv()

bot = Bot(os.environ["VK_API_KEY"])
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
cooldown = 0

SYSTEM_MSG = "You are an assistant. Answer in user's language."
SYSTEM_EMOJI = "⚙️"
AI_EMOJI = "🤖"
MAX_WIDTH = 750
BAN_WORDS = ("hitler", "гитлер", "gitler", "ниггер")


def num_tokens_from_string(string: str, model: str = "gpt-3.5-turbo") -> int:
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = len(encoding.encode(string))
    return num_tokens


def create_response(question: str, img: str = None, model: str = "gpt-3.5-turbo") -> str:
    if img is not None:
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
    else:
        response = client.chat.completions.create(
            model=model,
            max_tokens=1000,
            messages=[
                {"role": "system", "content": SYSTEM_MSG},
                {"role": "user", "content": question}
            ]
        )

    return f"{AI_EMOJI} {response.choices[0].message.content}"


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


def pick_img(sizes: list[PhotosPhotoSizes]) -> str:
    sizes_widths = [photo.width for photo in sizes]
    filtered_sizes = [size for size in sizes_widths if size <= MAX_WIDTH]

    if not filtered_sizes:
        closest_size = min(sizes_widths, key=lambda x: abs(x - MAX_WIDTH))
    else:
        closest_size = max(filtered_sizes)

    for photo in sizes:
        if photo.width == closest_size:
            photo_url = photo.url
            break

    return photo_url


@bot.on.message(text="!aihelp")
async def ai_help(message: Message):
    return (
        f"{SYSTEM_EMOJI} !ai <запрос> - запрос к боту (gpt-3.5-turbo)"
        "\n\nПри использовании этой команды, gpt получает ваш запрос и ваше имя и фамилию (соответственно, разрешая отправлять эти данные компании OpenAI)."
        "\n\nЕсли использовать эту команду, ответив на сообщение другого пользователя, то gpt получает ваш запрос, ваше имя и фамилию, текст сообщения в ответе и имя и фамилию пользователя в ответе."
    )


@bot.on.message(text=('!ai <question_user>', '!gpt3 <question_user>'))
async def ai_txt(message: Message, question_user: str):
    global cooldown
    if cooldown + 8 > time.time():
        return f"{SYSTEM_EMOJI} КулДаун!"

    if len(question_user) < 5:
        return f"{SYSTEM_EMOJI} В запросе должно быть больше 5 букв!"

    img_url = None
    if (
        message.attachments and
        message.attachments[0].type is MessagesMessageAttachmentType.PHOTO
    ):
        if message.from_id != 322615766:
            return f"{SYSTEM_EMOJI} Неа!"
        img_url = pick_img(message.attachments[0].photo.sizes)

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
        return f"{SYSTEM_EMOJI} В сообщении более 500 токенов ({num_tokens})! Используйте меньше слов."

    if any(ban_word in question.lower() for ban_word in BAN_WORDS):
        return f"{SYSTEM_EMOJI} Попробуй поговорить о чем-то другом. Поможет в развитии."

    try:
        flagged = is_flagged(question)
    except Exception as e:
        return f"{SYSTEM_EMOJI} Произошла ошибка во время модерации текста: {e}"

    if flagged[0] is True:
        return (
            f"{SYSTEM_EMOJI} Лил бро попытался забанить меня, но у него ничего не получилось :(\n"
            f"Запрос нарушает правила OpenAI: {flagged[1]}"
        )

    cooldown = time.time()
    try:
        if img_url is not None:
            ai_response = create_response(question, img_url, "gpt-4-vision-preview")
        else:
            ai_response = create_response(question)
    except Exception as e:
        return f"{SYSTEM_EMOJI} Чет пошло не так: {e}"

    return ai_response


if __name__ == "__main__":
    logger.info("Starting bot...")
    bot.run_forever()
