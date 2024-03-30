import os

import ai_stuff
from base import Conversation, Message, Prompt
from constants import (
    AI_EMOJI,
    HELP_MSG,
    SYSTEM_EMOJI,
)
from db import (
    get_user_created_moods,
    update_mood_value,
    create_account,
    create_tables,
    delete_account,
    get_mood,
    is_registered,
    get_user_mood,
    get_all_moods,
    update_value,
    create_mood
)
from dotenv import load_dotenv
from keyboards import OPEN_SETTINGS_KBD, SETTINGS_KBD
from loguru import logger
from openai import AsyncOpenAI
from utils import (
    moderate_query,
    moderate_result,
    process_instructions,
)
from vkbottle.bot import Bot
from vkbottle.bot import Message as VkMessage
from vkbottle import Keyboard
from vkbottle import KeyboardButtonColor as Color
from vkbottle import Text

load_dotenv()

bot = Bot(os.environ["VK_API_KEY"])
bot.labeler.vbml_ignore_case = True  # type: ignore
group_id = os.environ["VK_GROUP_ID"]
client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

msg_history: dict = {}
waiting_line = []


@bot.on.message(text="!aihelp")
async def ai_help_handler(_: VkMessage):
    return HELP_MSG


@bot.on.message(text=("!tokenize", "!tokenize <query>"))
async def count_tokens_handler(message: VkMessage, query: str | None = None):
    await message.get_user()

    if query is None and message.reply_message is None:
        return f"{SYSTEM_EMOJI} Эээ... А что токенизировать то?"

    if query is None:
        num_tokens = ai_stuff.num_tokens_from_string(message.reply_message.text)
    else:
        num_tokens = ai_stuff.num_tokens_from_string(query)

    ending = ('' if num_tokens == 1 else 'а' if num_tokens < 5 else 'ов')
    cost = num_tokens/1000*0.0015
    cost_rounded = "{:.5f}".format(cost)
    return f"{SYSTEM_EMOJI} В сообщении {num_tokens} токен{ending} (${cost_rounded})!"


@bot.on.message(text=('!ai <query>', '!gpt3 <query>'))
async def ai_txt_handler(message: VkMessage, query: str):
    try:
        user = await message.get_user(fields="bdate")
        full_name = user.first_name + " " + user.last_name
    except IndexError:
        # User is a group
        user = None
        full_name = "Anonymous"

    conv = Conversation([Message(query, str(message.from_id), full_name)])

    reply_user = None
    if message.reply_message is not None:
        try:
            reply_user = await message.reply_message.get_user()
            reply_full_name = reply_user.first_name + " " + reply_user.last_name
        except IndexError:
            # Reply user is a group
            reply_user = None
            reply_full_name = "Anonymous"
        conv.prepend(
            Message(
                message.reply_message.text,
                str(message.reply_message.from_id),
                reply_full_name
            )
        )

    conversation_text = conv.render()

    fail_reason = await moderate_query(conversation_text, client)
    if fail_reason:
        return fail_reason

    try:
        user_mood = await get_user_mood(message.from_id)
    except TypeError:
        # User is a group/User doesn't have an account
        # Using default assistant mood instead
        user_mood = await get_mood(0)

    user_mood_instr = user_mood[5]
    mood_instr = process_instructions(user_mood_instr, (user if reply_user is None else None))

    prompt = Prompt(
        header=Message(mood_instr),
        convo=conv
    )
    response = await ai_stuff.create_response(client, prompt)
    logger.info(response)

    moderated = moderate_result(response)
    if moderated[0] == 1:
        return moderated[1]

    response = moderated[1]
    await message.reply(f"{AI_EMOJI} {response}")


@bot.on.message(text=("начать", "!начать"))
async def start_handler(message: VkMessage):
    if message.from_id < 0:
        # Groups can't have an account
        return f"{SYSTEM_EMOJI} Нет, ботёнок, для создания аккаунта ты должен быть человеком!"

    if (await is_registered(message.from_id)):
        # Person is already registered
        return f"{SYSTEM_EMOJI} Гений, у тебя уже есть аккаунт в боте. Смирись с этим."

    await create_account(message.from_id)
    await message.answer(
        f"{SYSTEM_EMOJI} Аккаунт готов; теперь вы можете настраивать поведение бота!",
        keyboard=OPEN_SETTINGS_KBD
    )


@bot.on.message(text="!гптнастройки")
@bot.on.message(payload={"cmd": "settings"})
async def open_settings_handler(message: VkMessage):
    if not (await is_registered(message.from_id)):
        return f"{SYSTEM_EMOJI} Для этого надо зарегестрироваться!"

    user_mood = await get_user_mood(message.from_id)
    logger.info(user_mood)
    mood_id = user_mood[0]
    mood_name = user_mood[3]

    await message.answer(
        f"{SYSTEM_EMOJI} Текущий муд: {mood_name} (id: {mood_id})", keyboard=SETTINGS_KBD
    )


@bot.on.message(text=("!настроения", "!муды", "!кастомы"))
@bot.on.message(payload={"cmd": "change_gpt_mood_info"})
async def list_mood_handler(message: VkMessage):
    moods = await get_all_moods(public_only=True)
    if len(moods) == 0:
        return f"{SYSTEM_EMOJI} Публичных мудов в боте пока не существует!"

    all_moods_str = f"{SYSTEM_EMOJI} Вот все текущие публичные муды:"
    for i, mood in enumerate(moods, 1):
        mood_id = mood[0]
        mood_name = mood[3]
        all_moods_str += f"\n{i}. {mood_name} (id: {mood_id})"
    return all_moods_str


@bot.on.message(text=("!настроение <mood_id:int>", "!муд <mood_id:int>"))
async def custom_mood_info(message: VkMessage, mood_id: int):
    custom_mood = await get_mood(mood_id)
    not_exists_msg = f"{SYSTEM_EMOJI} Айди с таким мудом не существует или он приватный!"
    if not custom_mood or (custom_mood[2] == 0 and custom_mood[1] != message.from_id):
        return not_exists_msg

    mood_id, mood_creator_id, _, mood_name, mood_desc, mood_instr = custom_mood
    creator_info = (await bot.api.users.get(user_ids=[mood_creator_id], name_case="gen"))[0]
    creator_full_name_gen = f"{creator_info.first_name} {creator_info.last_name}"

    choose_this_kbd = (
        Keyboard(inline=True)
        .add(Text("Выбрать этот муд", payload={"set_mood_id": mood_id}), color=Color.PRIMARY)
    ).get_json()

    await message.answer(
        f"{SYSTEM_EMOJI} Муд от [id{mood_creator_id}|{creator_full_name_gen}] - id: {mood_id}"
        f"\n👤 | Имя: {mood_name}"
        f"\n🗒 | Описание: {mood_desc or '<Нету>'}"
        f"\n🤖 | Инструкции: {mood_instr}",
        keyboard=choose_this_kbd,
        disable_mentions=True,
    )


@bot.on.message(text="!поменять настроение <mood_id:int>")
@bot.on.message(payload_map=[("set_mood_id", int)])
async def change_mood_handler(message: VkMessage, mood_id: int | None = None):
    if not (await is_registered(message.from_id)):
        return (
            f"{SYSTEM_EMOJI} Гений, чтобы поменять муд,"
            " нужно сначала зарегаться командой \"!начать\"."
        )

    payload = message.get_payload_json()
    if mood_id is None:
        mood_id = payload["set_mood_id"]

    custom_mood = await get_mood(mood_id)
    if not custom_mood:
        return f"{SYSTEM_EMOJI} Такого муда не существует!"
    mood_id = custom_mood[0]
    mood_name = custom_mood[3]

    await update_value(message.from_id, "selected_mood_id", mood_id)
    return f"{SYSTEM_EMOJI} Вы успешно выбрали муд \"{mood_name}\" (id: {mood_id})"


@bot.on.message(text=("!создать муд", "!новый муд"))
async def custom_mood_info_handler(_: VkMessage):
    return (
        f"{SYSTEM_EMOJI} Чтобы создать новый муд,"
        " напишите \"!создать муд <инструкции>\""
        "\nИнструкции лучше всего писать на английском!"
        "\nНапример: You are now a cute anime girl. Don't forget to use :3 and other things"
        " that cute anime girls say. Speak only Russian."
    )


@bot.on.message(text=("!создать муд <instr>", "!новый муд <instr>"))
async def new_custom_mood_handler(message: VkMessage, instr: str | None = None):
    if not (await is_registered(message.from_id)):
        return (
            f"{SYSTEM_EMOJI} Гений, чтобы создать муд,"
            " нужно сначала зарегаться командой \"!начать\"."
        )

    fail_reason = await moderate_query(instr, client)
    if fail_reason:
        return fail_reason

    user_moods = await get_user_created_moods(message.from_id)
    if len(user_moods) >= 5:
        return f"{SYSTEM_EMOJI} Вы не можете создать больше 5 мудов!"

    # Creating mood
    inserted_id = await create_mood(message.from_id, "Мой муд", instr)

    # Adding new mood to this user's created moods
    user_moods.append(inserted_id)
    user_moods = [str(i) for i in user_moods]
    await update_value(message.from_id, "created_moods_ids", ','.join(user_moods))

    return (
        f"{SYSTEM_EMOJI} Вы создали новый муд! Его айди: {inserted_id}"
        "\nТеперь вы можете:"
        f"\n1. Поменять название, с помощью команды \"!муд имя {inserted_id} <название муда>\"."
        "\n2. Поменять описание, с помощью команды"
        f" \"!муд описание {inserted_id} <описание муда>\"."
        f"\n3. Сделать муд публичным, с помощью команды \"!муд видимость {inserted_id}\"."
        "\n4. Поменять его инструкции, если вам что-то не понравилось в них."
        f" Команда: \"!муд инструкции {inserted_id} <инструкции>\""
    )


@bot.on.message(text="!муд <params_str>")
async def customize_mood_handler(message: VkMessage, params_str: str):
    if not (await is_registered(message.from_id)):
        return (
            f"{SYSTEM_EMOJI} Что ты там менять собрался? У тебя даже аккаунта нет!"
            "\n... Поэтому можешь его создать, с помощью команды \"!начать\"."
        )
    params = params_str.split()
    logger.info(f"Got these params: {params}")
    try:
        mood_id = int(params[1])
    except (KeyError, ValueError):
        return (
            f"{SYSTEM_EMOJI} Ты чет не то написал, броу!"
            "\nДоступные параметры: имя, описание, видимость"
        )

    user_moods = await get_user_created_moods(message.from_id)
    if mood_id not in user_moods:
        return f"{SYSTEM_EMOJI} Гений, это не твой муд! Сделай его копию и меняй как хочешь."

    success_msg = ""
    if params[0] == "имя":
        mood_name = ' '.join(params[2:])
        fail_reason = await moderate_query(mood_name)
        if fail_reason:
            return fail_reason

        await update_mood_value(mood_id, "name", mood_name)
        success_msg = "Вы успешно поменяли название муда!"
    elif params[0] == "описание":
        mood_desc = ' '.join(params[2:])
        fail_reason = await moderate_query(mood_desc)
        if fail_reason:
            return fail_reason

        await update_mood_value(mood_id, "desc", mood_desc)
        success_msg = "Вы успешно поменяли описание муда!"
    elif params[0] == "видимость":
        mood = await get_mood(mood_id)
        visibility = mood[2]

        new_visibility = 1
        if visibility == 1:
            new_visibility = 0
        visibility_status = ('публичный' if new_visibility else 'приватный')

        await update_mood_value(mood_id, "visibility", new_visibility)
        success_msg = f"Вы успешно поменяли видимость муда на \"{visibility_status}\""
    elif params[0] == "инструкции":
        mood_instr = ' '.join(params[2:])
        fail_reason = await moderate_query(mood_instr, client)
        if fail_reason:
            return fail_reason

        await update_mood_value(mood_id, "instructions", mood_instr)
        success_msg = "Вы успешно поменяли инструкции муда!"
    else:
        return f"{SYSTEM_EMOJI} Эээ... Что? Такого параметра нету, уж извини!"
    return SYSTEM_EMOJI + " " + success_msg


@bot.on.message(text="!мои муды")
async def my_moods_handler(message: VkMessage):
    if not (await is_registered(message.from_id)):
        return (
            f"{SYSTEM_EMOJI} Гений, чтобы сделать муд,"
            " нужно сначала зарегаться командой \"!начать\"."
        )

    user_moods = await get_user_created_moods(message.from_id)
    if len(user_moods) == 0:
        return (
            f"{SYSTEM_EMOJI} Удивительно, но вы ещё не создавали собственный муд!"
            "\nЧтобы его создать, напишите \"!создать муд\""
        )

    user_moods_message = f"{SYSTEM_EMOJI} Ваши муды:"
    for i, mood in enumerate(user_moods, 1):
        pub_mood = await get_mood(mood)
        user_moods_message += f"\n{i}. {pub_mood[3]} (id: {pub_mood[0]})"

    return user_moods_message


@bot.on.message(text="!удалить гпт")
@bot.on.message(payload={"cmd": "delete_account"})
async def delete_account_handler(message: VkMessage):
    if not (await is_registered(message.from_id)):
        return (
            f"{SYSTEM_EMOJI} Пока мы живем в 2024, этот гений живет в 1488"
            "\nУ вас и так нет аккаунта. Отличная причина создать его!"
        )
    await delete_account(message.from_id)
    return f"{SYSTEM_EMOJI} Готово... но зачем?"


if __name__ == "__main__":
    logger.info("Starting bot...")
    bot.loop_wrapper.on_startup.append(create_tables())
    bot.run_forever()
