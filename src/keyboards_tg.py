from telegrinder import InlineButton, InlineKeyboard

OPEN_SETTINGS_KBD = (
    InlineKeyboard()
    .add(InlineButton(text="Настройки", callback_data="settings"))
).get_markup()

SETTINGS_KBD = (
    InlineKeyboard()
    .add(InlineButton(text="Поменять муд", callback_data="change_gpt_mood_info"))
    .row()
    .add(InlineButton(text="Удалить аккаунт", callback_data="delete_account"))
).get_markup()
