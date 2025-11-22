from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.constants import MODELS
from bot.database.models import UserModel
from bot.utils import find_model_by_id, find_model_by_request


async def add_user(
    session: AsyncSession, user_id: int, platform: str
) -> None:
    """Add a new user to the database."""
    new_user = UserModel(
        id=user_id,
        platform=platform
    )

    session.add(new_user)
    await session.commit()


async def get_user(
    session: AsyncSession, user_id: int
) -> UserModel | None:
    """Returns user's object from the database."""
    query = select(UserModel).filter_by(id=user_id).limit(1)

    result = await session.execute(query)

    user = result.scalar_one_or_none()
    return user


async def user_exists(session: AsyncSession, user_id: int) -> bool:
    """Checks if the user is in the database."""
    query = select(UserModel.id).filter_by(id=user_id).limit(1)

    result = await session.execute(query)

    user = result.scalar_one_or_none()
    return bool(user)


async def remove_user(
    session: AsyncSession, user_id: int
) -> None:
    """Removes user from the database."""
    query = delete(UserModel).where(UserModel.id == user_id)
    await session.execute(query)
    await session.commit()


async def update_user_value(session: AsyncSession, user_id: int, key, value) -> None:
    stmt = update(UserModel).where(UserModel.id == user_id).values({key: value})

    await session.execute(stmt)
    await session.commit()


async def get_user_model(session: AsyncSession, user_id: int) -> dict | None:
    """Return user's current model."""
    query = select(UserModel.current_model_id).filter_by(id=user_id).limit(1)

    result = await session.execute(query)

    model_id = result.scalar_one()
    if model_id.isdigit():
        model = find_model_by_id(MODELS, model_id)
        if model:
            model["source"] = "bot"
        return model
    else:
        model = await find_model_by_request(model_id)
        if model:
            model["source"] = "openrouter"
        return model
