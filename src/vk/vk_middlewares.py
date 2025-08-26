import asyncio
import random

from vkbottle import BaseMiddleware
from vkbottle.bot import Message

from constants import DONATION_MSG, DONATION_MSG_CHANCE
from database.database import sessionmaker


class DonationMsgMiddleware(BaseMiddleware[Message]):
    async def post(self):
        if not self.handlers:
            return
        if random.random() < DONATION_MSG_CHANCE:
            await asyncio.sleep(0.3)
            await self.event.answer(DONATION_MSG)


class DatabaseMiddleware(BaseMiddleware[Message]):
    async def pre(self):
        async with sessionmaker() as session:
            self.send({"session": session})
