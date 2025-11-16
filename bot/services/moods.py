from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import MoodModel, UserModel


async def add_mood(
    session: AsyncSession,
    user_id: int,
    name: str,
    instructions: str,
    is_private: bool,
    description: str = "",
) -> int:
    """Add a new mood to the database."""
    new_mood = MoodModel(
        user_id=user_id,
        name=name,
        description=description,
        instructions=instructions,
        is_private=is_private
    )

    session.add(new_mood)
    await session.flush()

    mood_id = new_mood.id

    await session.commit()
    return mood_id


async def get_all_moods(
    session: AsyncSession, user_id: int | None = None, public_only: bool = False
) -> list[MoodModel]:
    """Returns all moods from the database."""
    query = select(MoodModel)

    if user_id is not None:
        query = query.filter_by(user_id=user_id)

    if public_only:
        query = query.filter_by(is_private=False)

    result = await session.execute(query)

    moods = result.scalars()
    return list(moods)


async def get_mood(
    session: AsyncSession, mood_id: int
) -> MoodModel | None:
    """Returns a mood by its id from the database."""
    query = select(MoodModel).filter_by(id=mood_id).limit(1)

    result = await session.execute(query)

    user = result.scalar_one_or_none()
    return user


async def remove_mood(
    session: AsyncSession, mood_id: int
) -> None:
    """Removes a model from the database."""
    query = delete(MoodModel).where(MoodModel.id == mood_id)
    await session.execute(query)
    await session.commit()


async def update_mood_value(session: AsyncSession, mood_id: int, key, value) -> None:
    stmt = update(MoodModel).where(MoodModel.id == mood_id).values({key: value})

    await session.execute(stmt)
    await session.commit()


async def get_user_mood(session: AsyncSession, user_id: int) -> MoodModel | None:
    query = select(UserModel.current_mood_id).filter_by(id=user_id).limit(1)
    result = await session.execute(query)
    mood_id = result.scalar_one_or_none()
    if mood_id is None:
        return

    query = select(MoodModel).filter_by(id=mood_id).limit(1)
    result = await session.execute(query)
    mood = result.scalar_one_or_none()
    return mood