from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import UserModel


async def get_user(
    session: AsyncSession, user_id: int
) -> UserModel | None:
    """Returns user's object from the database."""
    query = select(UserModel).filter_by(id=user_id).limit(1)

    result = await session.execute(query)

    user = result.scalar_one_or_none()
    return user
