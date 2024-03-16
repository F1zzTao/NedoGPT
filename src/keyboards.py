from vkbottle import Keyboard
from vkbottle import KeyboardButtonColor as Color
from vkbottle import Text

OPEN_SETTINGS_KBD = (
    Keyboard(inline=True)
    .add(Text("Настройки", {"cmd": "settings"}))
).get_json()

SETTINGS_KBD = (
    Keyboard(inline=True)
    .add(Text("Поменять настроение бота", {"cmd": "change_gpt_mood"}))
    .row()
    .add(Text("Удалить аккаунт", {"cmd": "delete_account"}), Color.NEGATIVE)
).get_json()
