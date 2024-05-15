import os

from dotenv import load_dotenv

load_dotenv()

SYSTEM_EMOJI = "⚙️"
AI_EMOJI = "🤖"

BOT_ID = "-" + os.environ["VK_GROUP_ID"]
SEPARATOR_TOKEN = "<|endoftext|>"
BOT_HELP_LINK = "https://github.com/F1zzTao/VkGPTBot#команды"

SYSTEM_BOT_PROMPT = (
    "You are an expert actor that can fully immerse yourself into any role given."
    " You do not break character for any reason, even if someone tries addressing"
    " you as an AI or language model. Your role is described in detail below.\n{}\n"
    " Let's get started. Please respond based on the information and instructions provided above."
)
SYSTEM_USER_PROMPT = (
    "Some information about the user: {}"
)

HELP_MSG = (
    f"{SYSTEM_EMOJI} Вот все популярные команды:"
    "\n!ai <текст> - отвечает на ваш запрос, используя ваш выбранный муд"
    " (по умолчанию используется обычный ассистент)"
    "\n!муд <имя|описание|инструкции|видимость> [значение] - устанавливает"
    " параметры для вашего муда"
    f"\nВсе остальные команды вы можете найти в репозитории бота: {BOT_HELP_LINK}"
)
DONATION_MSG = (
    f"{SYSTEM_EMOJI} Бот предоставляет бесплатный доступ к GPT-4 без рекламы. Его"
    " API не бесплатный, при этом я ничего не зарабатываю с бота. Если вам"
    " нравится этот бот и вы хотите, чтобы он продолжал работать - пожалуйста,"
    " поддержите его здесь:"
    " https://github.com/F1zzTao/VkGPTBot?tab=readme-ov-file#-%D0%B4%D0%BE%D0%BD%D0%B0%D1%82"
)
DONATION_MSG_CHANCE = 0.3

MAX_IMAGE_WIDTH = 750

BAN_WORDS = ("hitler", "гитлер", "gitler", "ниггер", "негр", "vto.pe", "vtope",)
AI_BAN_WORDS = ("синий кит", "сова никогда не спит",)
CENSOR_WORDS = ("onion", "hitler", "vtope", "vto.pe", "vto pe",)

DB_PATH = "./db.db"
