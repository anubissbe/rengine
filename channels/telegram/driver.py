"""What the API needs from Telegram without running the listener: verify, notify, menu."""

from __future__ import annotations

from channels import commands
from channels.models import BotInfo
from channels.render import Line, chunk
from channels.telegram.api import SAFE_LIMIT, TelegramApi, TelegramError

__all__ = ["TelegramError", "menu", "notify", "verify"]


def menu() -> list[tuple[str, str]]:
    return [(spec.name, spec.title) for spec in commands.catalog().values()]


async def verify(token: str) -> BotInfo:
    api = TelegramApi(token)
    try:
        info = await api.get_me()
        await api.delete_webhook()
        await api.set_my_commands(menu())
    finally:
        await api.close()
    return info


async def notify(token: str, external_id: str, lines: list[Line]) -> None:
    api = TelegramApi(token)
    try:
        for message in chunk(lines, SAFE_LIMIT):
            await api.send_message(external_id, message.text, message.entities)
    finally:
        await api.close()
