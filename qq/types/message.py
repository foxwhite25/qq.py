from __future__ import annotations

from typing import List, Literal, Optional, TypedDict, Union

from .embed import Embed
from .member import Member
from .user import User
from ..utils import SnowflakeList


class Attachment(TypedDict, total=False):
    url: str


class _MessageOptional(TypedDict, total=False):
    guild_id: str


class Message(_MessageOptional):
    id: str
    channel_id: str
    author: User
    member: Member
    content: str
    timestamp: str
    edited_timestamp: Optional[str]
    mention_everyone: bool
    mentions: List[User]
    attachments: List[Attachment]
    embeds: List[Embed]


AllowedMentionType = Literal['roles', 'users', 'everyone']


class AllowedMentions(TypedDict):
    parse: List[AllowedMentionType]
    roles: SnowflakeList
    users: SnowflakeList
    replied_user: bool
