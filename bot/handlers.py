from typing import Literal, overload

from loguru import logger
from telegrinder.types import InlineKeyboardMarkup

from bot import ai_stuff
from bot.base import Conversation, Message, Prompt, UserInfo
from bot.core.config import HELP_MSG, OPENROUTER_HEADERS, Model, settings
from bot.database.database import sessionmaker
from bot.database.models import MoodModel, UserModel
from bot.services.generations import add_generation, count_generations
from bot.services.moods import (
    add_mood,
    get_all_moods,
    get_mood,
    get_user_mood,
    remove_mood,
    set_user_mood,
    update_mood_value,
)
from bot.services.users import (
    add_user,
    get_user,
    get_user_model,
    remove_user,
    set_user_model,
    update_user_value,
    user_exists,
)
from bot.tg import keyboards_tg
from bot.utils import (
    censor_result,
    find_model_by_id,
    find_model_by_request,
    is_model_free,
    moderate_query,
    process_main_prompt,
)
from bot.vk import keyboards_vk


async def handle_start(user_id: int, platform: str) -> tuple[str, bool]:
    # bool means if kbd should be returned or not
    if user_id < 0:
        # ? Does TG works the same way?
        # Groups can't have an account
        return (
            f"{settings.emojis.system} Нет, ботёнок, для создания аккаунта ты должен быть человеком!", False
        )

    async with sessionmaker() as session:
        if (await user_exists(session, user_id)):
            # Person is already registered
            return (f"{settings.emojis.system} Гений, у тебя уже есть аккаунт в боте. Смирись с этим.", False)

        await add_user(session, user_id, platform)
    return (f"{settings.emojis.system} Аккаунт готов; теперь вы можете настраивать поведение бота!", True)


def handle_help() -> str:
    return HELP_MSG


async def handle_ai(
    query: str,
    user: UserInfo,
    bot_id: str,
    reply_user: UserInfo | None = None,
    reply_query: str | None = None,
):
    async with sessionmaker() as session:
        db_user = await get_user(session, user.user_id)
        if not db_user:
            return (
                f"{settings.emojis.system} У вас нет аккаунта! Аккаунт в этом боте можно создать,"
                " написав команду \"!начать\""
            )

        conv = Conversation(
            [
                Message(
                    query,
                    str(user.user_id), user.full_name
                )
            ]
        )

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

        user_model = await get_user_model(session, user.user_id)
        if user_model is None:
            logger.warning(f"User {user.user_id}'s model doesn't exist anymore, fallback to default")

            default_model = find_model_by_id(settings.models, settings.default_model_id)
            if default_model is None:
                default_model = Model(id="0", name="???")

            await set_user_model(session, user.user_id, settings.default_model_id)

            return (
                f"{settings.emojis.system} Модели, которая у вас сейчас установлена, больше"
                " не существует. Мы автоматически поменяли её на модель по умолчанию"
                f" ({default_model.name})."
                "\nПопробуйте ввести команду ещё раз, или выберите другую модель в списке \"!модели\""
            )

        model_name = user_model.name
        if user_model.deprecation:
            if user_model.deprecation.is_deprecated:
                return (
                    f"{settings.emojis.system} Выбранная модель ({user_model.name}) устарела. Пожалуйста,"
                    " выберите другую через команду \"!модель <айди модели>\". Посмотреть все"
                    " модели можно командой \"!модели\""
                    )


        fail_reason = await moderate_query(conversation_text)
        if fail_reason:
            return fail_reason

        try:
            user_mood = await get_user_mood(session, user.user_id)
        except TypeError:
            # User is a group or he doesn't have an account
            # Defaulting to assistant mood
            user_mood = await get_mood(session, 0)

        if user_mood is None:
            raise ValueError("Couldn't find specified mood or assistant mood.")

        user_mood_instr = user_mood.instructions
        user_persona  = db_user.persona

    system_prompt = await process_main_prompt(
        system_prompt=settings.prompts.system_bot,
        persona_prompt=settings.prompts.system_user,
        mood=user_mood_instr,
        persona=user_persona
    )

    prompt = Prompt(
        headers=[
            Message(system_prompt),
        ],
        convo=conv
    )

    messages_rendered = None
    prompt_rendered = None
    if user_model.source == 'bot' and user_model.template:
        prompt_rendered = await prompt.full_render_template(bot_id, user_model.template)
    else:
        messages_rendered = prompt.full_render(bot_id)

    result = await ai_stuff.create_response(
        OPENROUTER_HEADERS, settings.OPENAI_BASE_URL, messages_rendered, prompt_rendered, model_name
    )

    if not result:
        return (
            f"{settings.emojis.system} Ответ от бота был съеден. Все равно он был невкусный (попробуйте ещё раз)."
        )

    if result["status"] == "error":
        return (
            f"{settings.emojis.system} Ошибка на стороне OpenRouter: {result['response']}"
        )


    response = result["response"]
    async with sessionmaker() as session:
        await add_generation(
            session,
            response,
            user.user_id,
            model_name,
            user_mood.id
        )

    cens_response = censor_result(response).strip()

    return cens_response


async def handle_settings(user_id: int) -> tuple[str, bool]:
    async with sessionmaker() as session:
        if not (await user_exists(session, user_id)):
            return (
                f"{settings.emojis.system} Для этого нужен аккаунт! Создайте его командой \"!начать\"",
                False
            )

        user_mood = await get_user_mood(session, user_id)
        logger.info(user_mood)
        if not user_mood:
            mood_id = 727727  # yup, that's osu! reference
            mood_name = "???"
            logger.warning(f"Couldnt' find {user_id}'s mood")
        else:
            mood_id = user_mood.id
            mood_name = user_mood.name

        user_model = await get_user_model(session, user_id)
    if not user_model:
        user_model = Model(id="0", name="???")

    if user_model.source == 'bot':
        model_name = user_model.name
        if user_model.deprecation:
            if user_model.deprecation.warning:
                model_name += " ⚠️"
    else:
        model_name = user_model.id

    current_model_string = (f"{user_model.display_name} ({model_name})" if user_model.display_name else model_name)

    return (
        f"{settings.emojis.system} | Текущий муд: {mood_name} (id: {mood_id})\n"
        f"🤖 | Текущая модель: {current_model_string}",
        True
    )


async def handle_mood_list() -> str:
    async with sessionmaker() as session:
        moods = await get_all_moods(
            session, public_only=True, sort_by_popularity=True
        )

    moods = moods[:10]

    if len(moods) == 0:
        return f"{settings.emojis.system} Публичных мудов в боте пока не существует!"

    all_moods_str = f"{settings.emojis.system} Все публичные муды:"
    for mood in moods:
        all_moods_str += f"\n• {mood[0].name} (id: {mood[0].id}){' - 👀 '+str(mood[1]) if mood[1] > 0 else ''}"
    return all_moods_str

@overload
async def handle_mood_page(offset: int, platform: Literal["vk"]) -> str | tuple[str, str]: ...
@overload
async def handle_mood_page(offset: int, platform: Literal["tg"]) -> str | tuple[str, InlineKeyboardMarkup]: ...

async def handle_mood_page(offset: int, platform: str) -> str | tuple[str, str | InlineKeyboardMarkup]:
    async with sessionmaker() as session:
        moods = await get_all_moods(
            session, public_only=True, sort_by_popularity=True
        )

    if len(moods) == 0:
        return f"{settings.emojis.system} Публичных мудов в боте пока не существует!"

    if offset < 0:
        offset = 0

    new_moods = moods[offset:offset+15]

    match platform:
        case "vk":
            kbd_page_generator = keyboards_vk.mood_page_generator
        case "tg":
            kbd_page_generator = keyboards_tg.mood_page_generator
        case _:
            raise TypeError(f"Unknown platform passed: {platform}")

    kbd = kbd_page_generator(has_left=(offset > 0), has_right=(len(moods[offset+15:]) > 0), offset=offset)

    all_moods_str = ""
    for mood in new_moods:
        all_moods_str += f"\n• {mood[0].name} (id: {mood[0].id}){' - 👀 '+str(mood[1]) if mood[1] > 0 else ''}"
    return (all_moods_str, kbd)


async def mood_exists(user_id: int, mood_id: int) -> str | MoodModel:
    async with sessionmaker() as session:
        mood = await get_mood(session, mood_id)

    if not mood or (mood.is_private is True and mood.user_id not in (str(user_id), settings.VK_ADMIN_ID)):
        # If this mood doesn't exists or it's private...
        return f"{settings.emojis.system} Айди с таким мудом не существует или он приватный!"
    return mood


async def handle_mood_info(mood: MoodModel, full_name: str | None = None) -> str:
    if full_name:
        mood_by = f"[id{mood.user_id}|{full_name}]"
    else:
        mood_by = "пользователя"

    async with sessionmaker() as session:
        generations = await count_generations(session, mood_id=mood.id)

    return (
        f"{settings.emojis.system} Муд от {mood_by} - id: {mood.id}"
        f"\n👀 | Всего генераций: {generations}"
        f"\n👤 | Имя: {mood.name}"
        f"\n🗒 | Описание: {mood.description or '<Нету>'}"
        f"\n🤖 | Инструкции: {mood.instructions}"
    )


async def handle_set_mood(user_id: int, mood_id: int) -> str:
    async with sessionmaker() as session:
        if not (await user_exists(session, user_id)):
            return f"{settings.emojis.system} Для этого нужен аккаунт! Создайте его командой \"!начать\""

        custom_mood = await get_mood(session, mood_id)
        if not custom_mood or (custom_mood.is_private is True and user_id != custom_mood.user_id):
            return f"{settings.emojis.system} Такого муда не существует!"
        mood_id = custom_mood.id
        mood_name = custom_mood.name

        await set_user_mood(session, user_id, mood_id)
    return f"{settings.emojis.system} Вы успешно выбрали муд \"{mood_name}\" (id: {mood_id})"


def handle_create_mood_info(cp: str = "!") -> str:
    return (
        f"{settings.emojis.system} Чтобы создать новый муд,"
        f" напишите \"{cp}создать муд <инструкции>\""
        "\nИнструкции лучше всего писать на английском!"
        "\nНапример: You are now a cute anime girl. Don't forget to use :3 and other things"
        " that cute anime girls say. Speak only Russian."
    )


async def handle_create_mood(user_id: int, instr: str, cp: str = "!") -> str:
    async with sessionmaker() as session:
        if not (await user_exists(session, user_id)):
            return (
                f"{settings.emojis.system} Гений, чтобы создать муд,"
                f" нужно сначала зарегаться командой \"{cp}начать\"."
            )

        fail_reason = await moderate_query(instr)
        if fail_reason:
            return fail_reason

        user_moods = await get_all_moods(session, user_id)
        if len(user_moods) >= 10 and str(user_id) != settings.VK_ADMIN_ID:
            return f"{settings.emojis.system} Вы не можете создать больше 10 мудов!"

        # Creating mood
        inserted_id = await add_mood(
            session, user_id, "Мой муд", instr, False
        )

    # TODO: Make a keyboard for choosing a just created mood

    return (
        f"{settings.emojis.system} Вы создали новый муд! Его айди: {inserted_id}"
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
    async with sessionmaker() as session:
        if not (await user_exists(session, user_id)):
            return (
                f"{settings.emojis.system} Что ты там менять собрался? У тебя даже аккаунта нет!"
                f"\n... Поэтому можешь его создать командой \"{cp}начать\"."
            )
        params = params_str.split()
        logger.info(f"Got these params: {params}")
        try:
            mood_id = int(params[1])
        except (KeyError, ValueError):
            return (
                f"{settings.emojis.system} Ты чет не то написал, броу!"
                "\nДоступные параметры: имя, описание, видимость"
            )

        mood = await get_mood(session, mood_id)
        if not mood or mood.user_id != user_id:
            return f"{settings.emojis.system} Гений, это не твой муд! Сделай его копию и меняй как хочешь."

        success_msg = ""
        if params[0] in ("имя", "название"):
            mood_name = ' '.join(params[2:])
            fail_reason = await moderate_query(mood_name)
            if fail_reason:
                return fail_reason

            await update_mood_value(session, mood_id, MoodModel.name, mood_name)
            success_msg = "Вы успешно поменяли название муда!"
        elif params[0] == "описание":
            mood_desc = ' '.join(params[2:])
            fail_reason = await moderate_query(mood_desc)
            if fail_reason:
                return fail_reason

            await update_mood_value(session, mood_id, MoodModel.description, mood_desc)
            success_msg = "Вы успешно поменяли описание муда!"
        elif params[0] == "видимость":
            visibility = mood.is_private

            new_is_private = True
            if visibility is True:
                new_is_private = False
            visibility_status = ('приватный' if new_is_private else 'публичный')

            await update_mood_value(session, mood_id, MoodModel.is_private, new_is_private)
            success_msg = f"Вы успешно поменяли видимость муда на \"{visibility_status}\""
        elif params[0] == "инструкции":
            mood_instr = ' '.join(params[2:])
            fail_reason = await moderate_query(mood_instr)
            if fail_reason:
                return fail_reason

            await update_mood_value(session, mood_id, MoodModel.instructions, mood_instr)
            success_msg = "Вы успешно поменяли инструкции муда!"
        else:
            return f"{settings.emojis.system} Эээ... Что? Такого параметра нету, уж извини!"
    return settings.emojis.system + " " + success_msg


async def handle_my_moods(user_id: int, cp: str = "!") -> str:
    async with sessionmaker() as session:
        if not (await user_exists(session, user_id)):
            return (
                f"{settings.emojis.system} Гений, чтобы сделать муд,"
                f" нужно сначала зарегаться командой \"{cp}начать\"."
            )

        user_moods = await get_all_moods(session, user_id)
        if len(user_moods) == 0:
            return (
                f"{settings.emojis.system} Удивительно, но вы ещё не создавали собственный муд!"
                f"\nЧтобы его создать, напишите \"{cp}создать муд\""
            )

        user_moods_message = f"{settings.emojis.system} Ваши муды:"
        for mood in user_moods:
            user_moods_message += f"\n• {mood.name} (id: {mood.id})"

    return user_moods_message


def handle_persona_info(cp: str = "!") -> str:
    return (
        f"{settings.emojis.system} Персону, как и инструкции, желательно писать на английском!"
        f"\nПример: {cp}персона I'm Hu Tao. I work in Wangsheng Funeral Parlor"
        " together with Zhongli. I have very long brown twintail hair and flower-shaped"
        " pupils."
    )


async def handle_set_persona(user_id: int, persona: str) -> str:
    async with sessionmaker() as session:
        if not (await user_exists(session, user_id)):
            return f"{settings.emojis.system} Для этого нужен аккаунт! Создайте его командой \"!начать\""

        fail_reason = await moderate_query(persona)
        if fail_reason:
            return fail_reason

        await update_user_value(session, user_id, UserModel.persona, persona)
    return f"{settings.emojis.system} Вы успешно установили персону!"


async def handle_my_persona(user_id: int) -> str:
    async with sessionmaker() as session:
        user = await get_user(session, user_id)
        if not user:
            return f"{settings.emojis.system} Для этого нужен аккаунт! Создайте его командой \"!начать\""

    if user.persona:
        msg = f"{settings.emojis.system} Вот ваша персона: {user.persona}"
    else:
        msg = f"{settings.emojis.system} У вас ещё не установлена персона!"
    return msg


async def handle_models_list(cp: str = "!") -> str:
    msg = f"{settings.emojis.system} Вот все текущие доступные модели бота:"
    for model in settings.models:
        if model.price > 0:
            model_price_text = f" - {model.price} 🍣"
        else:
            model_price_text = ""
        new_msg = f"\n• {model.name} (id: {model.id}){model_price_text}"

        if model.deprecation and model.deprecation.is_deprecated:
            # Model is deprecated, ignoring it
            continue
        if model.deprecation and model.deprecation.warning:
            # Model will become deprecated soon
            new_msg += " ⚠️"

        msg += new_msg

    msg += f"\n\nВыбрать модель можно с помощью команды \"{cp}модель <её айди>\""
    return msg


async def handle_set_model(user_id: int, model_string: str) -> str | None:
    async with sessionmaker() as session:
        if not (await user_exists(session, user_id)):
            return f"{settings.emojis.system} Для этого нужен аккаунт! Создайте его командой \"!начать\""

        is_custom = False
        if not model_string.isdigit():
            if len(model_string.split("/")) != 2:
                return

            is_free = await is_model_free(model_string)
            if isinstance(is_free, dict):
                model_price_prompt = float(is_free["prompt"])*1_000_000
                model_price_completed = float(is_free["completion"])*1_000_000
                return (
                    f"{settings.emojis.system} При выборе кастомной модели можно устанавливать только бесплатные модели,"
                    f" а эта стоит аж ${model_price_prompt}/М токенов + ${model_price_completed}/М токенов!"
                    " Дорого!!"
                )
            is_custom = True

        model_name = None
        model_openrouter_id = None
        if not is_custom:
            selected_model: Model | None = find_model_by_id(settings.models, model_string)
            if selected_model is None:
                return f"{settings.emojis.system} Модели с таким айди пока не существует!"

            if selected_model.deprecation and selected_model.deprecation.is_deprecated:
                return (
                    f"{settings.emojis.system} Модель {selected_model.name} устарела и больше не поддерживается,"
                    " пожалуйста выберите другую!"
                )
            model_name = selected_model.name
        else:
            model = await find_model_by_request(model_string)
            if not model:
                return f"{settings.emojis.system} Такой модели на OpenRouter не существует!"

            model_name = model.name
            model_openrouter_id = model.id

        await set_user_model(session, user_id, model_string)

    msg = (
        f"{settings.emojis.system} Вы успешно установили модель {model_name}!"
    )
    if not is_custom:
        if selected_model.deprecation and selected_model.deprecation.warning:
            msg += (
                "\n\n⚠️ Внимание: выбранная модель устарела и скоро будет удалена из бота. "
                "Используйте другую модель."
            )

        if selected_model.bad_russian:
            msg += (
                "\n\n⚠️ Внимание: выбранная модель была в основном натренирована на английских"
                " данных и с русским работает очень плохо. Рекомендуется использовать английский"
                " для данной модели."
            )
    else:
        msg += (
            f"\n\n⚠️ Внимание: вы выбрали кастомную модель с OpenRouter ({model_openrouter_id})."
            " Делать это не рекомендуется, так как качество и работа с русским кастомных моделей"
            " может сильно варьироваться. Используйте её только если вы знаете, что делаете."
        )
    return msg


async def handle_del_mood(user_id: int, mood_id: int) -> str:
    async with sessionmaker() as session:
        if not (await user_exists(session, user_id)):
            return f"{settings.emojis.system} Для этого нужен аккаунт! Создайте его командой \"!начать\""
        mood = await get_mood(session, mood_id)
        if not mood or (mood.user_id != user_id and str(user_id) != settings.VK_ADMIN_ID):
            return (
                f"{settings.emojis.system} Гений, это не твой муд. Если он тебя так раздражает,"
                " попроси его создателя удалить его."
            )

        await remove_mood(session, mood_id)
    return f"{settings.emojis.system} Ваш позорный муд удален и больше вас не позорит!"


async def handle_del_persona(user_id: int) -> str:
    async with sessionmaker() as session:
        if not (await user_exists(session, user_id)):
            return f"{settings.emojis.system} Для этого нужен аккаунт! Создайте его командой \"!начать\""

        await update_user_value(session, user_id, UserModel.persona, "")
    return f"{settings.emojis.system} Персона успешно удалена!"


async def handle_del_account_warning(user_id: int) -> str:
    async with sessionmaker() as session:
        if not (await user_exists(session, user_id)):
            return (
                f"{settings.emojis.system} Пока мы живем в 2025, этот гений живет в 2026"
                "\nУ вас и так нет аккаунта. Отличная причина создать его командой \"!начать\"!"
            )

        msg = (
            f"{settings.emojis.system} Вы уверены, что хотите удалить свой аккаунт?"
        )

        # ? Perhaps there's a better approach to handling account deletion when
        # user has created some moods?
        user_moods = await get_all_moods(session, user_id)
    if len(user_moods) > 0:
        msg += (
            f"\nВы создали муды ({len(user_moods)}). Удалив аккаунт, вы больше не"
            " сможете их редактировать, даже после создания нового аккаунта."
        )

    msg += "\nНапишите \"!точно удалить гпт\" чтобы его удалить."

    return msg


async def handle_del_account(user_id: int) -> str:
    async with sessionmaker() as session:
        if not (await user_exists(session, user_id)):
            return f"{settings.emojis.system} Для этого нужен аккаунт!"

        await remove_user(session, user_id)
    return f"{settings.emojis.system} Готово... но зачем?"
