from dataclasses import dataclass
from typing import List

import aiofiles
import yaml
from jinja2.sandbox import ImmutableSandboxedEnvironment

from constants import AI_EMOJI, INSTRUCTION_TEMPLATES_PATH, SEPARATOR_TOKEN


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
    headers: list[Message]
    convo: Conversation

    def full_render(self, bot_id: str) -> list[dict]:
        messages = []
        for header in self.headers:
            messages.append(
                {
                    "role": "system",
                    "content": header.render(),
                }
            )
        for message in self.render_messages(bot_id):
            messages.append(message)

        return messages

    async def full_render_template(self, bot_id: str, template_name: str) -> str:
        jinja_env = ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True)
        rendered = self.full_render(bot_id)

        async with aiofiles.open(
            f"{INSTRUCTION_TEMPLATES_PATH}/{template_name}.yaml", 'r', encoding='utf-8'
        ) as f:
            content = await f.read()
        data = yaml.safe_load(content)
        instruction_template_str = data['instruction_template']
        instruction_template = jinja_env.from_string(instruction_template_str)

        instruction = instruction_template.render(
            messages=rendered, add_generation_prompt=True
        )
        return instruction

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
                    "content": message.render(incl_full_name=False).replace(AI_EMOJI+' ', ''),
                }


@dataclass(frozen=True)
class UserInfo:
    user_id: int
    full_name: str
