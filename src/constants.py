import os

from dotenv import load_dotenv

load_dotenv()

SYSTEM_EMOJI = "⚙️"
AI_EMOJI = "🤖"

BOT_ID = "-" + os.environ["VK_GROUP_ID"]
SEPARATOR_TOKEN = "<|endoftext|>"
BOT_HELP_LINK = "https://github.com/F1zzTao/VkGPTBot#команды"

HELP_MSG = (
    f"{SYSTEM_EMOJI} Вот все популярные команды:"
    "\n!ai <текст> - отвечает на ваш запрос, используя ваш выбранный муд"
    " (по умолчанию используется обычный ассистент)"
    "\n!муд <имя|описание|инструкции|видимость> [значение] - устанавливает"
    " параметры для вашего муда"
    f"\nВсе остальные команды вы можете найти в репозитории бота: {BOT_HELP_LINK}"
)

MAX_IMAGE_WIDTH = 750

BAN_WORDS = ("hitler", "гитлер", "gitler", "ниггер", "негр", "vto.pe", "vtope",)
AI_BAN_WORDS = ("синий кит", "сова никогда не спит",)
CENSOR_WORDS = ("onion", "hitler", "vtope", "vto.pe", "vto pe",)

DB_PATH = "./db.db"
