from aiogram import Router, types
from aiogram.filters import Command, CommandObject
from loguru import logger

from bot import ai_stuff
from bot.base import Conversation, Message, Prompt, UserInfo
from bot.core.config import OPENROUTER_HEADERS, TG_BOT_ID, Model, settings
from bot.core.loader import dp
from bot.database.database import sessionmaker
from bot.services.generations import add_generation
from bot.services.moods import (
    get_mood,
    get_user_mood,
)
from bot.services.users import (
    get_user,
    get_user_model,
    set_user_model,
)
from bot.utils import (
    censor_result,
    find_model_by_id,
    moderate_query,
    process_main_prompt,
)

router = Router(name="ai")


@dp.message(Command(commands=["ai", "gpt"]))
async def ai_handler(message: types.Message, command: CommandObject):
    if not message.from_user:
        return

    if command.args is None:
        return

    full_name: str = message.from_user.full_name
    query: str = command.args

    reply_user = None
    reply_query = None
    if message.reply_to_message:
        reply_msg = message.reply_to_message
        if reply_msg.from_user:
            reply_query = reply_msg.text
            reply_full_name = reply_msg.from_user.full_name
            reply_user = UserInfo(reply_msg.from_user.id, reply_full_name)

    user = UserInfo(message.from_user.id, full_name)

    wait_msg = await message.reply(
        f"{settings.emojis.system} Генерируем ответ, пожалуйста подождите..."
    )

    async with sessionmaker() as session:
        db_user = await get_user(session, user.user_id)
        if not db_user:
            await wait_msg.edit_text(
                f"{settings.emojis.system} У вас нет аккаунта! Аккаунт в этом боте можно создать,"
                ' написав команду "/начать"'
            )
            return

        conv = Conversation([Message(query, str(user.user_id), user.full_name)])

        if reply_user:
            if reply_query is None:
                raise ValueError("Reply user is set but reply query is empty")
            reply_full_name = reply_user.full_name or "Anonymous"
            conv.prepend(Message(reply_query, str(reply_user.user_id), reply_full_name))

        conversation_text = conv.render(incl_full_name=False)

        user_model = await get_user_model(session, user.user_id)
        if user_model is None:
            logger.warning(
                f"User {user.user_id}'s model doesn't exist anymore, fallback to default"
            )

            default_model = find_model_by_id(settings.models, settings.default_model_id)
            if default_model is None:
                default_model = Model(id="0", name="???")

            await set_user_model(session, user.user_id, settings.default_model_id)

            await wait_msg.edit_text(
                f"{settings.emojis.system} Модели, которая у вас сейчас установлена, больше"
                " не существует. Мы автоматически поменяли её на модель по умолчанию"
                f" ({default_model.name})."
                '\nПопробуйте ввести команду ещё раз, или выберите другую модель в списке "!модели"'
            )
            return

        model_name = user_model.name
        if user_model.deprecation and user_model.deprecation.is_deprecated:
            await wait_msg.edit_text(
                f"{settings.emojis.system} Выбранная модель ({user_model.name}) устарела. Пожалуйста,"
                ' выберите другую через команду "!модель <айди модели>". Посмотреть все'
                ' модели можно командой "!модели"'
            )
            return

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
        user_persona = db_user.persona

    system_prompt = await process_main_prompt(
        system_prompt=settings.prompts.system_bot,
        persona_prompt=settings.prompts.system_user,
        mood=user_mood_instr,
        persona=user_persona,
    )

    prompt = Prompt(
        headers=[
            Message(system_prompt),
        ],
        convo=conv,
    )

    messages_rendered = None
    prompt_rendered = None
    if user_model.source == "bot" and user_model.template:
        prompt_rendered = await prompt.full_render_template(
            TG_BOT_ID, user_model.template
        )
    else:
        messages_rendered = prompt.full_render(TG_BOT_ID)

    result = await ai_stuff.create_response(
        OPENROUTER_HEADERS,
        settings.OPENAI_BASE_URL,
        messages_rendered,
        prompt_rendered,
        model_name,
    )

    if not result:
        await wait_msg.edit_text(
            f"{settings.emojis.system} Ответ от бота был съеден. Все равно он был невкусный (попробуйте ещё раз)."
        )
        return

    if result["status"] == "error":
        await wait_msg.edit_text(
            f"{settings.emojis.system} Ошибка на стороне OpenRouter: {result['response']}"
        )
        return

    response = result["response"]
    async with sessionmaker() as session:
        await add_generation(session, response, user.user_id, model_name, user_mood.id)

    cens_response = censor_result(response).strip()

    await wait_msg.edit_text(cens_response)
