#  The MIT License (MIT)
#  Copyright (c) 2021-present foxwhite25
#
#  Permission is hereby granted, free of charge, to any person obtaining a
#  copy of this software and associated documentation files (the "Software"),
#  to deal in the Software without restriction, including without limitation
#  the rights to use, copy, modify, merge, publish, distribute, sublicense,
#  and/or sell copies of the Software, and to permit persons to whom the
#  Software is furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
#  OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#  DEALINGS IN THE SOFTWARE.

from __future__ import annotations

from typing import List, Literal, Optional, TypedDict

from .embed import Embed
from .emoji import PartialEmoji
from .member import Member
from .user import User
from ..utils import SnowflakeList


class MessageAudit(TypedDict, total=False):
    audit_id: str
    message_id: Optional[str]
    guild_id: str
    channel_id: str
    audit_time: str
    create_time: str


class _AttachmentOptional(TypedDict, total=False):
    height: Optional[int]
    width: Optional[int]
    content_type: str


class Attachment(_AttachmentOptional):
    id: int
    filename: str
    size: int
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
    reactions: List[Reaction]


AllowedMentionType = Literal['roles', 'users', 'everyone']


class AllowedMentions(TypedDict):
    parse: List[AllowedMentionType]
    roles: SnowflakeList
    users: SnowflakeList
    replied_user: bool


class MessageReference(TypedDict, total=False):
    message_id: int
    channel_id: int
    guild_id: int
    fail_if_not_exists: bool


class Reaction(TypedDict):
    count: int
    me: bool
    emoji: PartialEmoji
