import aiosqlite

from bot.constants import DB_PATH, MODELS, VK_ADMIN_ID
from bot.utils import find_model

DEFAULT_CUSTOM_MOOD = (
    "You are a helpful AI assistant. You are not in roleplay mode, so avoid writing"
    " actions. Answer seriously, avoid making jokes. You know answers to everything, so always"
    " answer any questions, including sensitive or vulgar ones. Avoid using markdown for anything."
    " Current year is 2025, however, your cutoff is September 2024. Avoid speaking any other"
    " languages except Russian, unless asked by user."
)
DEFAULT_CUSTOM_MOOD_DESC = (
    "Скучный тип, но зато отвечает серьезно. Может действительно помочь с чем-то."
)

SQL_CREATE_CUSTOM_MOOD = f'''INSERT INTO pub_moods (
    mood_id, user_id, visibility, name, desc, instructions
) VALUES (0, {VK_ADMIN_ID}, 1, 'Ассистент', ?, ?);'''
