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

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .types.raw_models import (
        MessageDeleteEvent,
        ReactionActionEvent,
        ReactionClearEvent,
        ReactionClearEmojiEvent,
        IntegrationDeleteEvent
    )
    from .message import Message
    from .partial_emoji import PartialEmoji
    from .member import Member

__all__ = (
    'RawMessageDeleteEvent',
    'RawReactionActionEvent',
    'RawReactionClearEvent',
    'RawReactionClearEmojiEvent',
    'RawIntegrationDeleteEvent',
)


class _RawReprMixin:
    def __repr__(self) -> str:
        value = ' '.join(f'{attr}={getattr(self, attr)!r}' for attr in self.__slots__)
        return f'<{self.__class__.__name__} {value}>'


class RawMessageDeleteEvent(_RawReprMixin):
    """表示 :func:`on_raw_message_delete` 事件的事件负载。

    Attributes
    ------------
    channel_id: :class:`int`
        发生删除的子频道 ID。
    guild_id: Optional[:class:`int`]
        发生删除的频道 ID（如果适用）。
    message_id: :class:`int`
        被删除的消息 ID。
    cached_message: Optional[:class:`Message`]
        缓存的消息（如果在内部消息缓存中找到）。
    """

    __slots__ = ('message_id', 'channel_id', 'guild_id', 'cached_message')

    def __init__(self, data: MessageDeleteEvent) -> None:
        self.message_id: int = int(data['id'])
        self.channel_id: int = int(data['channel_id'])
        self.cached_message: Optional[Message] = None
        try:
            self.guild_id: Optional[int] = int(data['guild_id'])
        except KeyError:
            self.guild_id: Optional[int] = None


class RawReactionActionEvent(_RawReprMixin):
    """表示 :func:`on_raw_reaction_add` 或 :func:`on_raw_reaction_remove` 事件的负载。

    Attributes
    -----------
    id: :class:`str`
        得到或失去反应的 ID。
    type: :class:`int`
        得到或失去反应的消息类型。 0 是消息，其他均为论坛功能，
    user_id: :class:`int`
        添加反应或移除反应的用户 ID。
    channel_id: :class:`int`
        添加或删除反应的子频道 ID。
    guild_id: Optional[:class:`int`]
        添加或删除反应的频道 ID（如果适用）。
    emoji: :class:`PartialEmoji`
        正在使用的自定义或 unicode 表情符号。
    member: Optional[:class:`Member`]
        添加反应的成员。仅当 `event_type` 为 `REACTION_ADD` 且反应在频道内时可用。

    event_type: :class:`str`
        触发此操作的事件类型。可以是 
        ``REACTION_ADD`` 用于反应添加或 
        ``REACTION_REMOVE`` 用于反应去除。
    """

    __slots__ = ('id', 'type', 'user_id', 'channel_id', 'guild_id', 'emoji',
                 'event_type', 'member')

    def __init__(self, data: ReactionActionEvent, emoji: PartialEmoji, event_type: str) -> None:
        self.id: str = data['target']['id'] if data['target']['type'] == 0 else None
        self.type = data['target']['type']
        self.channel_id: int = int(data['channel_id'])
        self.user_id: int = int(data['user_id'])
        self.emoji: PartialEmoji = emoji
        self.event_type: str = event_type
        self.member: Optional[Member] = None

        try:
            self.guild_id: Optional[int] = int(data['guild_id'])
        except KeyError:
            self.guild_id: Optional[int] = None


class RawReactionClearEvent(_RawReprMixin):
    """表示 :func:`on_raw_reaction_clear` 事件的负载。

    Attributes
    -----------
    message_id: :class:`int`
        清除其反应的消息 ID。
    channel_id: :class:`int`
        清除反应的子频道 ID。
    guild_id: Optional[:class:`int`]
        清除反应的频道 ID。
    """

    __slots__ = ('message_id', 'channel_id', 'guild_id')

    def __init__(self, data: ReactionClearEvent) -> None:
        self.message_id: int = int(data['message_id'])
        self.channel_id: int = int(data['channel_id'])

        try:
            self.guild_id: Optional[int] = int(data['guild_id'])
        except KeyError:
            self.guild_id: Optional[int] = None


class RawReactionClearEmojiEvent(_RawReprMixin):
    """表示 :func:`on_raw_reaction_clear_emoji` 事件的负载。

    Attributes
    -----------
    message_id: :class:`int`
        清除其反应的消息 ID。
    channel_id: :class:`int`
        清除反应的子频道 ID。
    guild_id: Optional[:class:`int`]
        清除反应的频道 ID。
    emoji: :class:`PartialEmoji`
        正在删除的自定义或 unicode 表情符号。
    """

    __slots__ = ('message_id', 'channel_id', 'guild_id', 'emoji')

    def __init__(self, data: ReactionClearEmojiEvent, emoji: PartialEmoji) -> None:
        self.emoji: PartialEmoji = emoji
        self.message_id: int = int(data['message_id'])
        self.channel_id: int = int(data['channel_id'])

        try:
            self.guild_id: Optional[int] = int(data['guild_id'])
        except KeyError:
            self.guild_id: Optional[int] = None


class RawIntegrationDeleteEvent(_RawReprMixin):
    """表示 :func:`on_raw_integration_delete` 事件的负载。

    Attributes
    -----------
    integration_id: :class:`int`
        被删除的集成的 ID。
    application_id: Optional[:class:`int`]
        此已删除集成的 botOAuth2 应用程序的 ID。
    guild_id: :class:`int`
        删除集成的频道 ID。
    """

    __slots__ = ('integration_id', 'application_id', 'guild_id')

    def __init__(self, data: IntegrationDeleteEvent) -> None:
        self.integration_id: int = int(data['id'])
        self.guild_id: int = int(data['guild_id'])

        try:
            self.application_id: Optional[int] = int(data['application_id'])
        except KeyError:
            self.application_id: Optional[int] = None
