from vkbottle import Callback, Keyboard, Text
from vkbottle import KeyboardButtonColor as Color

OPEN_SETTINGS_KBD = (
    Keyboard(inline=True)
    .add(Text("Настройки", {"cmd": "settings"}))
).get_json()

SETTINGS_KBD = (
    Keyboard(inline=True)
    .add(Text("Поменять муд", {"cmd": "change_gpt_mood_info"}))
    .row()
    .add(Text("Поменять модель", {"cmd": "change_model"}), Color.NEGATIVE)
).get_json()


def mood_page_generator(
    has_left: bool = False,
    has_right: bool = False,
    offset: int = 0
) -> str:
    keyboard = Keyboard(inline=True)

    if has_left:
        keyboard.add(Callback("⬅️", payload={"cmd": "mood_page", "offset": offset-15}))
    if has_right:
        keyboard.add(Callback("➡️", payload={"cmd": "mood_page", "offset": offset+15}))

    return keyboard.get_json()