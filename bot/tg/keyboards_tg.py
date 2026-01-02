from telegrinder import InlineButton, InlineKeyboard
from telegrinder.types import InlineKeyboardMarkup

OPEN_SETTINGS_KBD = (
    InlineKeyboard()
    .add(InlineButton(text="Настройки", callback_data="settings"))
).get_markup()

SETTINGS_KBD = (
    InlineKeyboard()
    .add(InlineButton(text="Поменять муд", callback_data="moods/0"))
    .row()
    .add(InlineButton(text="Поменять модель", callback_data="change_model"))
).get_markup()


def mood_page_generator(
    has_left: bool = False,
    has_right: bool = False,
    offset: int = 0
) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboard()

    if has_left:
        keyboard.add(InlineButton("⬅️", callback_data=f"moods/{offset-15}"))
    if has_right:
        keyboard.add(InlineButton("➡️", callback_data=f"moods/{offset+15}"))

    return keyboard.get_markup()