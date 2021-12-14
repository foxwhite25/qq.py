from typing import TypedDict, List
from .member import Member
from .emoji import PartialEmoji


class _MessageEventOptional(TypedDict, total=False):
    guild_id: str


class MessageDeleteEvent(_MessageEventOptional):
    id: str
    channel_id: str


class BulkMessageDeleteEvent(_MessageEventOptional):
    ids: List[str]
    channel_id: str


class _ReactionActionEventOptional(TypedDict, total=False):
    guild_id: str
    member: Member


class MessageUpdateEvent(_MessageEventOptional):
    id: str
    channel_id: str


class ReactionActionEvent(_ReactionActionEventOptional):
    user_id: str
    channel_id: str
    message_id: str
    emoji: PartialEmoji


class _ReactionClearEventOptional(TypedDict, total=False):
    guild_id: str


class ReactionClearEvent(_ReactionClearEventOptional):
    channel_id: str
    message_id: str


class _ReactionClearEmojiEventOptional(TypedDict, total=False):
    guild_id: str


class ReactionClearEmojiEvent(_ReactionClearEmojiEventOptional):
    channel_id: int
    message_id: int
    emoji: PartialEmoji


class _IntegrationDeleteEventOptional(TypedDict, total=False):
    application_id: str


class IntegrationDeleteEvent(_IntegrationDeleteEventOptional):
    id: str
    guild_id: str
