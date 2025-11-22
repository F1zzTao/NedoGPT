import os

import yaml
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

with open("config.yaml") as f:
    CONFIG = yaml.safe_load(f)

OPENAI_TOKEN: str | None = os.getenv("OPENAI_API_KEY")
if OPENAI_TOKEN is None:
    raise ValueError("Token is not set in config!")

OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL") or "https://openrouter.ai/api/v1"

# HTTP-Referer: link to your website
# X-Title: name of your project, will be displayed in openrouter.ai leaderboards
OPENROUTER_HEADERS = {
    "Authorization": f"Bearer {OPENAI_TOKEN}",
    "HTTP-Referer": "https://vk.com/public205906217",
    "X-Title": "NedoGPT",
}

VK_TOKEN: str | None = os.getenv("VK_API_KEY")
VK_BOT_ID: str | None = os.getenv("VK_GROUP_ID")
VK_ADMIN_ID: str | None = os.getenv("VK_ADMIN_ID")
if VK_TOKEN is None and VK_BOT_ID is None and VK_ADMIN_ID is None:
    logger.error("VK config is not set, it will not work")

TG_TOKEN: str | None = os.getenv("TG_API_KEY")
if not TG_TOKEN:
    logger.error("Telegram config is not set, it will not work")

MODELS: list[dict] = CONFIG["models"]

# Default model is set after registration
DEFAULT_MODEL_ID: str = CONFIG["default_model_id"]

SYSTEM_EMOJI: str = CONFIG["emojis"]["system"]
AI_EMOJI: str = CONFIG["emojis"]["ai"]

BOT_HELP_LINK: str = CONFIG["links"]["bot_help_link"]
BOT_DONATE_LINK: str = CONFIG["links"]["bot_donate_link"]

SYSTEM_BOT_PROMPT: str = CONFIG["prompts"]["system_bot"]
SYSTEM_USER_PROMPT: str = CONFIG["prompts"]["system_user"]

# TODO: i18n
HELP_MSG: str = (
    f"{SYSTEM_EMOJI} Вот все популярные команды:"
    "\n!ai <текст> - отвечает на ваш запрос, используя ваш выбранный муд"
    " (по умолчанию используется обычный ассистент)"
    "\n!муд <имя|описание|инструкции|видимость> [значение] - устанавливает"
    " параметры для вашего муда"
    f"\nВсе остальные команды вы можете найти в репозитории бота: {BOT_HELP_LINK}"
)
DONATION_MSG: str = (
    f"{SYSTEM_EMOJI} На данный момент, бот предоставляет бесплатный доступ к моделям"
    " OpenRouter без рекламы. Сами модели не всегда бесплатные, при этом я ничего"
    " не зарабатываю с бота. Если вы хотите, чтобы бот продолжал работать - пожалуйста,"
    " поддержите его здесь:"
    " https://github.com/F1zzTao/NedoGPT?tab=readme-ov-file#-%D0%B4%D0%BE%D0%BD%D0%B0%D1%82"
)
DONATION_MSG_CHANCE: float = CONFIG["donation_msg_chance"]

MAX_IMAGE_WIDTH: int = CONFIG["max_image_width"]

CENSOR_WORDS: tuple = CONFIG["vk_censor_words"]

DB_PATH: str = CONFIG["paths"]["db"]
INSTRUCTION_TEMPLATES_PATH: str = CONFIG["paths"]["instruction_templates"]

# TODO: Remove
SEPARATOR_TOKEN = "<|endoftext|>"
