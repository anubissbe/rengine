"""The channel contract: what arrives, and how a reply leaves."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar

from channels.render import Line, Message, chunk


@dataclass(frozen=True)
class Inbound:
    channel: str
    external_id: str
    sender_id: str
    username: str | None
    first_name: str | None
    text: str
    message_id: str | None
    private: bool

    @property
    def display(self) -> str:
        if self.username:
            return f"@{self.username}"
        return (self.first_name or self.external_id).strip()


class Channel(ABC):
    kind: ClassVar[str]
    limit: ClassVar[int]

    @abstractmethod
    async def send(self, external_id: str, message: Message) -> str | None:
        """Deliver one message; returns its id when the channel has one."""

    async def edit(
        self,
        external_id: str,
        message_id: str,  # noqa: ARG002
        message: Message,
    ) -> None:
        await self.send(external_id, message)

    async def delete(self, external_id: str, message_id: str) -> None:  # noqa: ARG002
        return None

    async def reply(self, external_id: str, lines: list[Line]) -> str | None:
        last: str | None = None
        for message in chunk(lines, self.limit):
            last = await self.send(external_id, message)
        return last
