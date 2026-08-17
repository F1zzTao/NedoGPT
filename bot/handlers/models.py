from aiogram import F, Router, types
from aiogram.filters import Command, CommandObject

from bot.core.config import Model, settings
from bot.core.loader import dp
from bot.database.database import sessionmaker
from bot.services.users import set_user_model, user_exists
from bot.utils import find_model_by_id, find_model_by_request, is_model_free

router = Router(name="models")


@dp.message(Command(commands=["models", "модели"]))
async def model_list_handler(message: types.Message):
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

    msg += '\n\nВыбрать модель можно с помощью команды "/модель <её айди>"'
    await message.answer(msg)


@dp.callback_query(F.data == "change_model")
async def model_list_callback_handler(cb: types.CallbackQuery):
    # TODO: Repeated code from above (`model_list_handler`)
    if not cb.message or isinstance(cb.message, types.InaccessibleMessage):
        await cb.answer()
        return

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

    msg += '\n\nВыбрать модель можно с помощью команды "/модель <её айди>"'
    await cb.message.edit_text(msg)
    await cb.answer()


@dp.message(Command(commands=["model", "модель"]))
async def set_model_handler(message: types.Message, command: CommandObject):
    if not message.from_user:
        return

    if command.args is None:
        # TODO: Return current model if no args
        return

    user_id = message.from_user.id
    model_string = command.args

    async with sessionmaker() as session:
        if not (await user_exists(session, user_id)):
            await message.answer(f'{settings.emojis.system} Для этого нужен аккаунт! Создайте его командой "/начать"')
            return

        is_admin: bool = False
        if str(user_id) == settings.TG_ADMIN_ID:
            is_admin = True

        model_price_prompt: float = 0.0
        model_price_completed: float = 0.0
        is_custom = False
        if not model_string.isdigit():
            if len(model_string.split("/")) != 2:
                return

            is_free = await is_model_free(model_string)
            if isinstance(is_free, dict):
                # The model is not free if returned object is a dict
                model_price_prompt = round(float(is_free["prompt"]) * 1_000_000, 3)
                model_price_completed = round(
                    float(is_free["completion"]) * 1_000_000, 3
                )

            if not is_free and not is_admin:
                await message.answer(
                    f"{settings.emojis.system} При выборе кастомной модели можно устанавливать только бесплатные модели,"
                    f" а эта стоит аж ${model_price_prompt}/М токенов + ${model_price_completed}/М токенов!"
                    " Дорого!!"
                )
                return

            is_custom = True

        model_name = None
        model_openrouter_id = None
        if not is_custom:
            selected_model: Model | None = find_model_by_id(
                settings.models, model_string
            )
            if selected_model is None:
                await message.answer(
                    f"{settings.emojis.system} Модели с таким айди пока не существует!"
                )
                return

            if selected_model.deprecation and selected_model.deprecation.is_deprecated:
                await message.answer(
                    f"{settings.emojis.system} Модель {selected_model.name} устарела и больше не поддерживается,"
                    " пожалуйста выберите другую!"
                )
                return

            model_name = selected_model.name
        else:
            model = await find_model_by_request(model_string)
            if not model:
                await message.answer(
                    f"{settings.emojis.system} Такой модели на OpenRouter не существует!"
                )
                return

            model_name = model.name
            model_openrouter_id = model.id

        await set_user_model(session, user_id, model_string)

    msg = f"{settings.emojis.system} Вы успешно установили модель {model_name}!"
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
        if model_price_prompt > 0 and model_price_completed > 0:
            msg += (
                f"\n\n💸 Выбрана платная модель (${model_price_prompt}/М токенов input"
                f" + ${model_price_completed}/М токенов output)."
            )

    await message.answer(msg)
