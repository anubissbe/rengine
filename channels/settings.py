"""Channel settings, read from and written to the channel's config row."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

from channels.models import BotInfo, ChannelConfig
from mcp.capabilities import DEFAULT_CEILING
from shared.definitions.channels import DEFAULT_RATE_LIMIT
from shared.enums.api_key import APIProvider
from shared.services.api_key.async_api_key import APIKeyService
from shared.services.scan_resolve import MASK
from shared.utils.datetime import utc_now

_RATE = "rate_limit_per_minute"
_CEILING = "ceiling"
_BOT = "bot"
_STARTED = "started_at"

TELEGRAM_TOKEN_RE = re.compile(r"^\d{5,15}:[A-Za-z0-9_-]{20,64}$")


@dataclass
class ChannelSettings:
    enabled: bool = False
    rate_limit_per_minute: int = DEFAULT_RATE_LIMIT
    ceiling: dict[str, bool] = field(default_factory=dict)
    bot: BotInfo | None = None
    started_at: datetime | None = None

    def __post_init__(self) -> None:
        self.ceiling = {**DEFAULT_CEILING, **(self.ceiling or {})}


def read(row: ChannelConfig | None) -> ChannelSettings:
    if row is None:
        return ChannelSettings()
    blob = dict(row.settings or {})
    bot = blob.get(_BOT)
    return ChannelSettings(
        enabled=bool(row.enabled),
        rate_limit_per_minute=int(blob.get(_RATE, DEFAULT_RATE_LIMIT)),
        ceiling={**DEFAULT_CEILING, **(blob.get(_CEILING) or {})},
        bot=BotInfo(**bot) if isinstance(bot, dict) and bot.get("username") else None,
        started_at=row.started_at,
    )


def write(row: ChannelConfig, settings: ChannelSettings) -> None:
    row.enabled = settings.enabled
    row.started_at = settings.started_at
    row.settings = {
        _RATE: settings.rate_limit_per_minute,
        _CEILING: settings.ceiling,
        _BOT: settings.bot.model_dump() if settings.bot else None,
    }
    row.updated_at = utc_now()


async def bot_token(session) -> str | None:
    """The Telegram API key, shared with notifications."""
    return await APIKeyService(session).get_key_for_provider(APIProvider.TELEGRAM)


def mask_secret(secret: str | None) -> str | None:
    """The bot id before the colon is public; everything after it is not."""
    if not secret:
        return None
    head, sep, _ = secret.partition(":")
    return f"{head}{sep}{MASK}" if sep else MASK


def valid_telegram_token(value: str) -> bool:
    return bool(TELEGRAM_TOKEN_RE.match(value.strip()))


def redact(text: str, secret: str | None) -> str:
    """Strip a bot token from any string that might be logged or shown."""
    if not secret:
        return text
    return text.replace(secret, MASK)
