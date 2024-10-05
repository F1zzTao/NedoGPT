from sqlite3 import Row

from loguru import logger

import ai_stuff
from base import Conversation, Message, Prompt, UserInfo
from constants import (
    AI_EMOJI,
    HELP_MSG,
    MODEL_IDS,
    OPENAI_BASE_URL,
    OPENROUTER_HEADERS,
    SYSTEM_BOT_PROMPT,
    SYSTEM_EMOJI,
    VK_ADMIN_ID
)
from db import (
    create_account,
    create_balance,
    create_mood,
    delete_account,
    delete_mood,
    get_all_moods,
    get_mood,
    get_user_created_moods,
    get_user_model,
    get_user_mood,
    get_value,
    increase_value,
    is_registered,
    update_mood_value,
    update_value
)
from utils import moderate_query, moderate_result, process_instructions


async def handle_start(user_id: int, platform: str) -> tuple[str, bool]:
    # bool means if kbd should be returned ot not
    if user_id < 0:
        # ? Does TG works the same way?
        # Groups can't have an account
        return (
            f"{SYSTEM_EMOJI} Нет, ботёнок, для создания аккаунта ты должен быть человеком!", False
        )

    if (await is_registered(user_id)):
        # Person is already registered
        return (f"{SYSTEM_EMOJI} Гений, у тебя уже есть аккаунт в боте. Смирись с этим.", False)

    await create_account(user_id, platform)
    return (f"{SYSTEM_EMOJI} Аккаунт готов; теперь вы можете настраивать поведение бота!", True)


def handle_help() -> str:
    return HELP_MSG


async def handle_ai(
    query: str,
    user: UserInfo,
    bot_id: int,
    reply_user: UserInfo | None = None,
    reply_query: str | None = None,
):
    conv = Conversation([Message(query, str(user.user_id), user.full_name)])

    if reply_user:
        if reply_query is None:
            raise ValueError("Reply user is set but reply query is empty")
        reply_full_name = reply_user.full_name or "Anonymous"
        conv.prepend(
            Message(
                reply_query,
                str(reply_user.user_id),
                reply_full_name
            )
        )

    conversation_text = conv.render(incl_full_name=False)

    user_model: dict | None = await get_user_model(user.user_id)
    if not user_model:
        return (
            f"{SYSTEM_EMOJI} Ваша выбранная модель была удалена! Выберите другую."
            "\nПосмотреть все модели можно командой \"!модели\"."
        )

    model_name: str = user_model['name']
    if user_model.get("deprecation"):
        if user_model["deprecation"]["is_deprecated"]:
            return (
                f"{SYSTEM_EMOJI} Выбранная модель ({user_model['name']}) устарела. Пожалуйста,"
                " выберите другую через команду \"!модель <айди модели>\". Посмотреть все"
                " модели можно командой \"!модели\""
            )

    model_price = user_model['price']
    balance = await get_value(user.user_id, "sushi_amount", "sushi_balance")

    if balance is None:
        await create_balance(user.user_id)
    # elif balance <= model_price:
    #     return (
    #         f"{SYSTEM_EMOJI} Ты недостаточно покормил разработчика сушами, негодяй!!"
    #         f"\nИспользование этой модели стоит {model_price} суш, а у тебя всего {balance} 🍣!"
    #     )

    fail_reason = await moderate_query(conversation_text)
    if fail_reason:
        return fail_reason

    try:
        user_mood = await get_user_mood(user.user_id)
    except TypeError:
        # User is a group or he doesn't have an account
        # Defaulting to assistant mood
        user_mood = await get_mood(0)

    if user_mood is None:
        raise ValueError("Couldn't find specified mood or assistant mood.")

    user_mood_instr = user_mood[5]
    mood_instr = await process_instructions(
        user_mood_instr,
        (user.user_id if reply_user is None else None),
    )

    system_prompt = SYSTEM_BOT_PROMPT+'\n'+mood_instr

    prompt = Prompt(
        headers=[
            Message(system_prompt),
        ],
        convo=conv
    )

    messages_rendered = None
    prompt_rendered = None
    if user_model['template']:
        prompt_rendered = await prompt.full_render_template(str(bot_id), user_model['template'])
    else:
        messages_rendered = prompt.full_render(str(bot_id))

    response = await ai_stuff.create_response(
        OPENROUTER_HEADERS, OPENAI_BASE_URL, messages_rendered, prompt_rendered, model_name
    )
    logger.info(response)

    if not response:
        return (
            f"{SYSTEM_EMOJI} Ответ от бота был съеден. Все равно он был невкусный (модерация)."
        )

    moderated = moderate_result(response)
    if moderated[0] == 1:
        return moderated[1]

    response = moderated[1].strip()

    # Taking some sushi from the user
    # await increase_value(user.user_id, "sushi_amount", -model_price, "sushi_balance")
    msg_reply = f"{AI_EMOJI} {response}"

    return msg_reply


async def handle_settings(user_id: int) -> tuple[str, bool]:
    if not (await is_registered(user_id)):
        return (f"{SYSTEM_EMOJI} Для этого надо зарегестрироваться!", False)

    user_mood = await get_user_mood(user_id)
    logger.info(user_mood)
    mood_id = user_mood[0]
    mood_name = user_mood[3]

    user_model = await get_user_model(user_id)
    model_name = user_model['name']
    if user_model.get("deprecation"):
        if user_model["deprecation"]["warning"]:
            model_name += " ⚠️"

    sushi_amount: int = await get_value(user_id, "sushi_amount", "sushi_balance") or 0

    return (
        f"{SYSTEM_EMOJI} | Текущий муд: {mood_name} (id: {mood_id})\n"
        f"🤖 | Текущая модель: {model_name}\n"
        f"🍣 | Ваши суши: {sushi_amount}",
        True
    )


async def handle_mood_list() -> str:
    moods = await get_all_moods(public_only=True)
    if len(moods) == 0:
        return f"{SYSTEM_EMOJI} Публичных мудов в боте пока не существует!"

    all_moods_str = f"{SYSTEM_EMOJI} Вот все текущие публичные муды:"
    for mood in moods:
        mood_id = mood[0]
        mood_name = mood[3]
        all_moods_str += f"\n• {mood_name} (id: {mood_id})"
    return all_moods_str


async def mood_exists(user_id: int, mood_id: int) -> str | Row:
    mood = await get_mood(mood_id)
    if not mood or (mood[2] == 0 and mood[1] not in (user_id, VK_ADMIN_ID)):
        return f"{SYSTEM_EMOJI} Айди с таким мудом не существует или он приватный!"
    return mood


async def handle_mood_info(mood, full_name: str | None = None) -> str:
    mood_id, mood_creator_id, _, mood_name, mood_desc, mood_instr = mood
    if full_name:
        mood_by = f"[id{mood_creator_id}|{full_name}]"
    else:
        mood_by = "пользователя"

    return (
        f"{SYSTEM_EMOJI} Муд от {mood_by} - id: {mood_id}"
        f"\n👤 | Имя: {mood_name}"
        f"\n🗒 | Описание: {mood_desc or '<Нету>'}"
        f"\n🤖 | Инструкции: {mood_instr}"
    )


async def handle_set_mood(user_id: int, mood_id: int) -> str:
    if not (await is_registered(user_id)):
        return f"{SYSTEM_EMOJI} Для этого надо зарегестрироваться!"

    custom_mood = await get_mood(mood_id)
    if not custom_mood or (custom_mood[2] == 0 and user_id != custom_mood[1]):
        return f"{SYSTEM_EMOJI} Такого муда не существует!"
    mood_id = custom_mood[0]
    mood_name = custom_mood[3]

    await update_value(user_id, "selected_mood_id", mood_id)
    return f"{SYSTEM_EMOJI} Вы успешно выбрали муд \"{mood_name}\" (id: {mood_id})"


def handle_create_mood_info(cp: str = "!") -> str:
    return (
        f"{SYSTEM_EMOJI} Чтобы создать новый муд,"
        f" напишите \"{cp}создать муд <инструкции>\""
        "\nИнструкции лучше всего писать на английском!"
        "\nНапример: You are now a cute anime girl. Don't forget to use :3 and other things"
        " that cute anime girls say. Speak only Russian."
    )


async def handle_create_mood(user_id: str, instr: str, cp: str = "!") -> str:
    if not (await is_registered(user_id)):
        return (
            f"{SYSTEM_EMOJI} Гений, чтобы создать муд,"
            f" нужно сначала зарегаться командой \"{cp}начать\"."
        )

    fail_reason = await moderate_query(instr)
    if fail_reason:
        return fail_reason

    user_moods = await get_user_created_moods(user_id)
    if len(user_moods) >= 10 and user_id != VK_ADMIN_ID:
        return f"{SYSTEM_EMOJI} Вы не можете создать больше 10 мудов!"

    # Creating mood
    inserted_id = await create_mood(user_id, "Мой муд", instr)

    # Adding new mood to this user's created moods
    user_moods.append(inserted_id)
    user_moods = [str(i) for i in user_moods]
    await update_value(user_id, "created_moods_ids", ','.join(user_moods))

    # TODO: Make a keyboard for choosing a just created mood

    return (
        f"{SYSTEM_EMOJI} Вы создали новый муд! Его айди: {inserted_id}"
        "\nТеперь вы можете:"
        f"\n1. Поменять название, с помощью команды \"{cp}муд имя {inserted_id} <название муда>\"."
        "\n2. Поменять описание, с помощью команды"
        f" \"{cp}муд описание {inserted_id} <описание муда>\"."
        f"\n3. Сделать муд публичным, с помощью команды \"{cp}муд видимость {inserted_id}\"."
        "\n4. Поменять его инструкции, если вам что-то не понравилось в них."
        f" Команда: \"{cp}муд инструкции {inserted_id} <инструкции>\""
    )


async def handle_edit_mood(
    user_id: int, params_str: str, cp: str = "!"
) -> str:
    if not (await is_registered(user_id)):
        return (
            f"{SYSTEM_EMOJI} Что ты там менять собрался? У тебя даже аккаунта нет!"
            f"\n... Поэтому можешь его создать, с помощью команды \"{cp}начать\"."
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

    user_moods = await get_user_created_moods(user_id)
    if mood_id not in user_moods:
        return f"{SYSTEM_EMOJI} Гений, это не твой муд! Сделай его копию и меняй как хочешь."

    success_msg = ""
    if params[0] in ("имя", "название"):
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
        fail_reason = await moderate_query(mood_instr)
        if fail_reason:
            return fail_reason

        await update_mood_value(mood_id, "instructions", mood_instr)
        success_msg = "Вы успешно поменяли инструкции муда!"
    else:
        return f"{SYSTEM_EMOJI} Эээ... Что? Такого параметра нету, уж извини!"
    return SYSTEM_EMOJI + " " + success_msg


async def handle_my_moods(user_id: int, cp: str = "!") -> str:
    if not (await is_registered(user_id)):
        return (
            f"{SYSTEM_EMOJI} Гений, чтобы сделать муд,"
            f" нужно сначала зарегаться командой \"{cp}начать\"."
        )

    user_moods = await get_user_created_moods(user_id)
    if len(user_moods) == 0:
        return (
            f"{SYSTEM_EMOJI} Удивительно, но вы ещё не создавали собственный муд!"
            f"\nЧтобы его создать, напишите \"{cp}создать муд\""
        )

    user_moods_message = f"{SYSTEM_EMOJI} Ваши муды:"
    for mood in user_moods:
        pub_mood = await get_mood(mood)
        user_moods_message += f"\n• {pub_mood[3]} (id: {pub_mood[0]})"

    return user_moods_message


def handle_persona_info(cp: str = "!") -> str:
    return (
        f"{SYSTEM_EMOJI} Персону, как и инструкции, желательно писать на английском!"
        f"\nПример: {cp}персона I'm Hu Tao. I work in Wangsheng Funeral Parlor"
        " together with Zhongli. I have very long brown twintail hair and flower-shaped"
        " pupils."
    )


async def handle_set_persona(user_id: int, persona: str) -> str:
    if not (await is_registered(user_id)):
        return f"{SYSTEM_EMOJI} Для этого нужен аккаунт!"

    fail_reason = await moderate_query(persona)
    if fail_reason:
        return fail_reason

    await update_value(user_id, "persona", persona)
    return f"{SYSTEM_EMOJI} Вы успешно установили персону!"


async def handle_my_persona(user_id: int) -> str:
    if not (await is_registered(user_id)):
        return f"{SYSTEM_EMOJI} Для этого нужен аккаунт!"

    persona = await get_value(user_id, "persona")
    if persona:
        msg = f"{SYSTEM_EMOJI} Вот ваша персона: {persona}"
    else:
        msg = f"{SYSTEM_EMOJI} У вас ещё не установлена персона!"
    return msg


async def handle_models_list(cp: str = "!") -> str:
    msg = f"{SYSTEM_EMOJI} Вот все текущие доступные модели:"
    for model_id in MODEL_IDS:
        model = MODEL_IDS[model_id]['name']
        model_price = MODEL_IDS[model_id]['price']
        if model_price:
            model_price_text = f" - {MODEL_IDS[model_id]['price']} 🍣"
        else:
            model_price_text = ""
        new_msg = f"\n• {model} (id: {model_id}){model_price_text}"

        deprecation_info: dict | None = MODEL_IDS[model_id].get("deprecation")
        if deprecation_info and deprecation_info["is_deprecated"]:
            # Model is deprecated, ignoring it
            continue
        if deprecation_info and deprecation_info["warning"]:
            # Model will become deprecated soon
            new_msg += " ⚠️"

        msg += new_msg

    msg += f"\n\nВыбрать модель можно с помощью команды \"{cp}модель <её айди>\""
    return msg


async def handle_set_model(user_id: int, model_id: int) -> str:
    selected_model: dict | None = MODEL_IDS.get(model_id)
    if selected_model is None:
        return f"{SYSTEM_EMOJI} Модели с таким айди пока не существует!"

    if selected_model.get("deprecation") and selected_model["deprecation"]["is_deprecated"]:
        return (
            f"{SYSTEM_EMOJI} Модель {selected_model['name']} устарела и больше не поддерживается,"
            " пожалуйста выберите другую!"
        )

    await update_value(user_id, "selected_model_id", model_id)

    msg = (
        f"{SYSTEM_EMOJI} Вы успешно установили модель {selected_model['name']}!"
    )
    if selected_model.get("deprecation") and selected_model["deprecation"]["warning"]:
        msg += (
            "\n\n⚠️ Внимание: выбранная модель устарела и скоро будет удалена из бота. "
            "Используйте другую модель."
        )

    if selected_model['bad_russian']:
        msg += (
            "\n\n⚠️ Внимание: выбранная модель была в основном натренирована на английских"
            " данных и с русским работает очень плохо. Рекомендуется использовать английский"
            " для данной модели."
        )
    return msg


async def handle_del_mood(user_id: int, mood_id: int) -> str:
    if not (await is_registered(user_id)):
        return f"{SYSTEM_EMOJI} Для этого нужен аккаунт!"
    user_moods = await get_user_created_moods(user_id)
    if mood_id not in user_moods or user_id != VK_ADMIN_ID:
        return (
            f"{SYSTEM_EMOJI} Гений, это не твой муд. Если он тебя так раздражает,"
            " попроси его создателя удалить его."
        )

    await delete_mood(mood_id, user_id)
    return f"{SYSTEM_EMOJI} Ваш позорный муд удален и больше вас не позорит!"


async def handle_del_persona(user_id: int) -> str:
    if not (await is_registered(user_id)):
        return f"{SYSTEM_EMOJI} Для этого нужен аккаунт!"

    await update_value(user_id, "persona", None)
    return f"{SYSTEM_EMOJI} Персона успешно удалена!"


async def handle_del_account_warning(user_id: int) -> str:
    if not (await is_registered(user_id)):
        return (
            f"{SYSTEM_EMOJI} Пока мы живем в 2024, этот гений живет в 2025"
            "\nУ вас и так нет аккаунта. Отличная причина создать его!"
        )

    return (
        f"{SYSTEM_EMOJI} Вы уверены, что хотите удалить свой аккаунт?"
        " Напишите \"!точно удалить гпт\" чтобы его удалить."
    )


async def handle_del_account(user_id: int) -> str:
    if not (await is_registered(user_id)):
        return f"{SYSTEM_EMOJI} Для этого нужен аккаунт!"

    await delete_account(user_id)
    return f"{SYSTEM_EMOJI} Готово... но зачем?"


async def handle_admin_give_currency(user_id: int, value: int) -> str:
    has_balance = await get_value(user_id, "user_id", "sushi_balance")
    if not has_balance:
        return f"{SYSTEM_EMOJI} У [id{user_id}|этого] пользователя нету профиля!"

    await increase_value(user_id, "sushi_amount", value, "sushi_balance")
    return f"{SYSTEM_EMOJI} [id{user_id}|Этому] пользователю было выдано {value} суши!"
