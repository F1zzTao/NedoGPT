from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

OPEN_SETTINGS_KBD = InlineKeyboardBuilder(
    [[InlineKeyboardButton(text="Настройки", callback_data="settings")]]
).as_markup()

SETTINGS_KBD = InlineKeyboardBuilder(
    [
        [InlineKeyboardButton(text="Поменять муд", callback_data="moods/0")],
        [InlineKeyboardButton(text="Поменять модель", callback_data="change_model")],
    ]
).as_markup()


def mood_page_generator(
    has_left: bool = False, has_right: bool = False, offset: int = 0
) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()

    if has_left:
        keyboard.button(text="⬅️", callback_data=f"moods/{offset - 15}")
    if has_right:
        keyboard.button(text="➡️", callback_data=f"moods/{offset + 15}")

    return keyboard.as_markup()


def choose_mood_generator(mood_id: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder(
        [
            [
                InlineKeyboardButton(
                    text="Выбрать этот муд", callback_data=f"mood_id/{mood_id}"
                )
            ]
        ]
    )

    return keyboard.as_markup()
