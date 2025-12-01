from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cache.redis import build_key, cached, clear_cache
from bot.database.models import GenerationsModel


async def add_generation(
    session: AsyncSession,
    response: str,
    user_id: int,
    model: str,
    mood_id: int,
) -> int:
    """Add a new mood to the database."""
    new_gen = GenerationsModel(
        response=response,
        user_id=user_id,
        model=model,
        mood_id=mood_id,
    )

    session.add(new_gen)
    await session.flush()

    gen_id = new_gen.id

    await session.commit()
    await clear_cache(count_generations, gen_id)
    return gen_id


@cached(key_builder=lambda session, user_id=None: build_key(user_id))
async def count_generations(session: AsyncSession, user_id: int | None = None) -> int:
    query = select(func.count(GenerationsModel.id))
    if user_id is not None:
        query = query.filter(GenerationsModel.user_id == user_id)

    result = await session.execute(query)
    gen_count = result.scalar_one()
    return gen_count
