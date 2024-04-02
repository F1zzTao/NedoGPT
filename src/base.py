from dataclasses import dataclass
from typing import List

from constants import SEPARATOR_TOKEN


@dataclass(frozen=True)
class Message:
    text: str
    user_id: str | None = None
    full_name: str | None = None

    def render(self, incl_full_name: bool = True):
        result = self.text
        if self.full_name and incl_full_name:
            result = self.full_name + ": " + result
        return result


@dataclass
class Conversation:
    messages: List[Message]

    def prepend(self, message: Message):
        self.messages.insert(0, message)
        return self

    def render(self, incl_full_name: bool = True):
        return f"\n{SEPARATOR_TOKEN}".join(
            [message.render(incl_full_name) for message in self.messages]
        )


@dataclass(frozen=True)
class Prompt:
    header: Message
    convo: Conversation

    def full_render(self, bot_id: str):
        messages = [
            {
                "role": "system",
                "content": self.header.render(),
            }
        ]
        for message in self.render_messages(bot_id):
            messages.append(message)
        return messages

    def render_messages(self, bot_id: str):
        for message in self.convo.messages:
            if bot_id not in message.user_id:
                yield {
                    "role": "user",
                    "name": message.user_id,
                    "content": message.render(),
                }
            else:
                yield {
                    "role": "assistant",
                    "name": bot_id,
                    "content": message.render(incl_full_name=False),
                }
