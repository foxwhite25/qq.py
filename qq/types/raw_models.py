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

from typing import TypedDict, List

from .emoji import PartialEmoji
from .member import Member


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


class Target(TypedDict, total=False):
    id: str
    type: int


class ReactionActionEvent(_ReactionActionEventOptional):
    user_id: str
    channel_id: str
    target: Target
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
