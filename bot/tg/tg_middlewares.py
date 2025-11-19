from telegrinder import ABCMiddleware, Context, Message

from database.database import sessionmaker


class DatabaseMiddleware(ABCMiddleware):
    async def pre(self, message: Message, context: Context) -> bool:
        async with sessionmaker() as session:
            context.session = session
        return True