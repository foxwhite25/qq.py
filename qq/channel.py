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

from typing import TYPE_CHECKING, Iterable, Optional, List

from . import abc
from .enum import ChannelType, try_enum
from .mixins import Hashable
from .object import Object

__all__ = (
    'TextChannel',
    'VoiceChannel',
    'LiveChannel',
    'AppChannel',
    'CategoryChannel',
    'ThreadChannel',
    'PartialMessageable',
)


if TYPE_CHECKING:
    from .member import Member
    from .message import Message, PartialMessage
    from .state import ConnectionState
    from .guild import Guild, GuildChannel as GuildChannelType
    from .types.channel import (
        TextChannel as TextChannelPayload,
        VoiceChannel as VoiceChannelPayload,
        CategoryChannel as CategoryChannelPayload,
        LiveChannel as LiveChannelPayload,
        AppChannel as AppChannelPayload,
        ThreadChannel as ThreadChannelPayload
    )


async def _single_delete_strategy(messages: Iterable[Message]):
    for m in messages:
        await m.delete()


class TextChannel(abc.Messageable, abc.GuildChannel, Hashable):
    """代表 QQ 频道中的文字子频道

    .. container:: operations
        .. describe:: x == y

            检查两个子频道是否相等。

        .. describe:: x != y

            检查两个子频道是否不相等。

        .. describe:: hash(x)

            返回子频道的哈希值。

        .. describe:: str(x)

            返回子频道的名称。

    Attributes
    -----------
    name: :class:`str`
        子频道的名称。
    guild: :class:`Guild`
        子频道所属的频道。
    id: :class:`int`
        子频道 ID。
    private_type: :class:`int`
        子频道私密类型。

        +----+---------------------+
        | 值 | 含义                |
        +----+---------------------+
        | 0  | 公开频道            |
        +----+---------------------+
        | 1  | 群主管理员可见      |
        +----+---------------------+
        | 2  | 群主管理员+指定成员 |
        +----+---------------------+

    category_id: Optional[:class:`int`]
        这个子频道属于的分类频道，如果没有则返回 ``None`` 。
    position: :class:`int`
        在子频道列表中的位置。 这是一个从 0 开始的数字。例如顶部子频道是位置 0。
    last_message_id: Optional[:class:`int`]
        发送到此通道的消息的最后一个消息 ID。 它可能 *不* 指向现有的或有效的消息。

    """

    __slots__ = (
        'name',
        'id',
        'guild',
        '_state',
        'category_id',
        'position',
        '_type',
        'last_message_id',
        'private_type'
    )

    def __init__(self, *, state: ConnectionState, guild: Guild, data: TextChannelPayload):
        self._state: ConnectionState = state
        self.id: int = int(data['id'])
        self._type: int = data['type']
        self.last_message_id: Optional[int] = None
        self._update(guild, data)

    def __repr__(self) -> str:
        attrs = [
            ('id', self.id),
            ('name', self.name),
            ('position', self.position),
            ('category_id', self.category_id),
        ]
        joined = ' '.join('%s=%r' % t for t in attrs)
        return f'<{self.__class__.__name__} {joined}>'

    def _update(self, guild: Guild, data: TextChannelPayload) -> None:
        self.guild: Guild = guild
        self.name: str = data['name']
        self.category_id: Optional[int] = int(data.get('parent_id'))
        self.position: int = data['position']
        self._type: int = data.get('type', self._type)
        self.private_type: int = data.get('private_type')

    async def _get_channel(self):
        return self

    @property
    def type(self) -> ChannelType:
        return try_enum(ChannelType, self._type)

    @property
    def _sorting_bucket(self) -> int:
        return ChannelType.text.value

    @property
    def members(self) -> List[Member]:
        """List[:class:`Member`]: 返回可以看到此子频道的所有成员。"""
        return [m for m in self.guild.members]

    def get_partial_message(self, message_id: int, /) -> PartialMessage:
        """从消息 ID 创建一个 :class:`PartialMessage`。
        如果您想处理消息并且只有它的 ID 而不进行不必要的 API 调用，这将非常有用。

        Parameters
        ------------
        message_id: :class:`int`
            要为其创建部分消息的消息 ID。
        Returns
        ---------
        :class:`PartialMessage`
            部分消息。
        """

        from .message import PartialMessage

        return PartialMessage(channel=self, id=message_id)


class VoiceChannel(abc.GuildChannel, Hashable):
    """表示 QQ 语音子频道。

    .. container:: operations

        .. describe:: x == y

            检查两个子频道是否相等。

        .. describe:: x != y

            检查两个子频道是否不相等。

        .. describe:: hash(x)

            返回子频道的哈希值。

        .. describe:: str(x)

            返回子频道的名称。

    Attributes
    -----------
    name: :class:`str`
        子频道名称。
    guild: :class:`Guild`
        子频道所属的频道。
    id: :class:`int`
        频道 ID。
    private_type: :class:`int`
        子频道私密类型。

        +----+---------------------+
        | 值 | 含义                |
        +----+---------------------+
        | 0  | 公开频道            |
        +----+---------------------+
        | 1  | 群主管理员可见      |
        +----+---------------------+
        | 2  | 群主管理员+指定成员 |
        +----+---------------------+

    position: :class:`int`
        在类别列表中的位置。 这是一个从 0 开始的数字。例如顶部频道是位置 0。
    """
    __slots__ = (
        'name',
        'id',
        'guild',
        '_state',
        'position',
        'category_id',
        'private_type'
    )

    def __init__(self, *, state: ConnectionState, guild: Guild, data: VoiceChannelPayload):
        self._state: ConnectionState = state
        self.id: int = int(data['id'])
        self._update(guild, data)

    def _update(self, guild: Guild, data: VoiceChannelPayload) -> None:
        self.guild = guild
        self.name: str = data['name']
        self.category_id: Optional[int] = int(data.get('parent_id'))
        self.position: int = data['position']
        self.private_type: int = data.get('private_type')

    def __repr__(self) -> str:
        attrs = [
            ('id', self.id),
            ('name', self.name),
            ('position', self.position),
            ('category_id', self.category_id),
        ]
        joined = ' '.join('%s=%r' % t for t in attrs)
        return f'<{self.__class__.__name__} {joined}>'


class LiveChannel(abc.GuildChannel, Hashable, abc.Messageable):
    """表示 QQ 直播子频道。

    .. container:: operations

        .. describe:: x == y

            检查两个子频道是否相等。

        .. describe:: x != y

            检查两个子频道是否不相等。

        .. describe:: hash(x)

            返回子频道的哈希值。

        .. describe:: str(x)

            返回子频道的名称。

    Attributes
    -----------
    name: :class:`str`
        子频道名称。
    guild: :class:`Guild`
        子频道所属的频道。
    id: :class:`int`
        频道 ID。
    private_type: :class:`int`
        子频道私密类型。

        +----+---------------------+
        | 值 | 含义                |
        +----+---------------------+
        | 0  | 公开频道            |
        +----+---------------------+
        | 1  | 群主管理员可见      |
        +----+---------------------+
        | 2  | 群主管理员+指定成员 |
        +----+---------------------+

    position: :class:`int`
        在类别列表中的位置。 这是一个从 0 开始的数字。例如顶部频道是位置 0。
    """

    __slots__ = (
        'name',
        'id',
        'guild',
        '_state',
        'position',
        'category_id',
        'private_type'
    )

    def __init__(self, *, state: ConnectionState, guild: Guild, data: LiveChannelPayload):
        self._state: ConnectionState = state
        self.id: int = int(data['id'])
        self._update(guild, data)

    def _update(self, guild: Guild, data: LiveChannelPayload) -> None:
        self.guild = guild
        self.name: str = data['name']
        self.category_id: Optional[int] = int(data.get('parent_id'))
        self.position: int = data['position']
        self.private_type: int = data.get('private_type')

    def __repr__(self) -> str:
        attrs = [
            ('id', self.id),
            ('name', self.name),
            ('position', self.position),
            ('category_id', self.category_id),
        ]
        joined = ' '.join('%s=%r' % t for t in attrs)
        return f'<{self.__class__.__name__} {joined}>'


class AppChannel(abc.GuildChannel, Hashable):
    """表示 QQ 应用子频道。

    .. container:: operations

        .. describe:: x == y

            检查两个子频道是否相等。

        .. describe:: x != y

            检查两个子频道是否不相等。

        .. describe:: hash(x)

            返回子频道的哈希值。

        .. describe:: str(x)

            返回子频道的名称。

    Attributes
    -----------
    name: :class:`str`
        子频道名称。
    guild: :class:`Guild`
        子频道所属的频道。
    id: :class:`int`
        频道 ID。
    private_type: :class:`int`
        子频道私密类型。

        +----+---------------------+
        | 值 | 含义                |
        +----+---------------------+
        | 0  | 公开频道            |
        +----+---------------------+
        | 1  | 群主管理员可见      |
        +----+---------------------+
        | 2  | 群主管理员+指定成员 |
        +----+---------------------+

    position: :class:`int`
        在类别列表中的位置。 这是一个从 0 开始的数字。例如顶部频道是位置 0。
    """
    __slots__ = (
        'name',
        'id',
        'guild',
        '_state',
        'position',
        'category_id',
        'private_type'
    )

    def __init__(self, *, state: ConnectionState, guild: Guild, data: AppChannelPayload):
        self._state: ConnectionState = state
        self.id: int = int(data['id'])
        self._update(guild, data)

    def _update(self, guild: Guild, data: AppChannelPayload) -> None:
        self.guild = guild
        self.name: str = data['name']
        self.category_id: Optional[int] = int(data.get('parent_id'))
        self.position: int = data['position']
        self.private_type: int = data.get('private_type')

    def __repr__(self) -> str:
        attrs = [
            ('id', self.id),
            ('name', self.name),
            ('position', self.position),
            ('category_id', self.category_id),
        ]
        joined = ' '.join('%s=%r' % t for t in attrs)
        return f'<{self.__class__.__name__} {joined}>'


class ThreadChannel(abc.GuildChannel, Hashable):
    """表示 QQ 论坛子频道。

    .. container:: operations

        .. describe:: x == y

            检查两个子频道是否相等。

        .. describe:: x != y

            检查两个子频道是否不相等。

        .. describe:: hash(x)

            返回子频道的哈希值。

        .. describe:: str(x)

            返回子频道的名称。

    Attributes
    -----------
    name: :class:`str`
        子频道名称。
    guild: :class:`Guild`
        子频道所属的频道。
    id: :class:`int`
        频道 ID。
    private_type: :class:`int`
        子频道私密类型。

        +----+---------------------+
        | 值 | 含义                |
        +----+---------------------+
        | 0  | 公开频道            |
        +----+---------------------+
        | 1  | 群主管理员可见      |
        +----+---------------------+
        | 2  | 群主管理员+指定成员 |
        +----+---------------------+

    position: :class:`int`
        在类别列表中的位置。 这是一个从 0 开始的数字。例如顶部频道是位置 0。
    """
    __slots__ = (
        'name',
        'id',
        'guild',
        '_state',
        'position',
        'category_id',
        'private_type'
    )

    def __init__(self, *, state: ConnectionState, guild: Guild, data: ThreadChannelPayload):
        self._state: ConnectionState = state
        self.id: int = int(data['id'])
        self._update(guild, data)

    def _update(self, guild: Guild, data: ThreadChannelPayload) -> None:
        self.guild = guild
        self.name: str = data['name']
        self.category_id: Optional[int] = int(data.get('parent_id'))
        self.position: int = data['position']
        self.private_type: int = data.get('private_type')

    def __repr__(self) -> str:
        attrs = [
            ('id', self.id),
            ('name', self.name),
            ('position', self.position),
            ('category_id', self.category_id),
        ]
        joined = ' '.join('%s=%r' % t for t in attrs)
        return f'<{self.__class__.__name__} {joined}>'


class CategoryChannel(abc.GuildChannel, Hashable):
    """表示 QQ 频道类别。
    这些对于将频道分组到逻辑区间很有用。

    .. container:: operations

        .. describe:: x == y

            检查两个频道是否相等。

        .. describe:: x != y

            检查两个频道是否不相等。

        .. describe:: hash(x)

            返回类别的哈希值。

        .. describe:: str(x)

            返回类别的名称。

    Attributes
    -----------
    name: :class:`str`
        类别名称。
    guild: :class:`Guild`
        类别所属的公会。
    id: :class:`int`
        类别频道 ID。
    private_type: :class:`int`
        子频道私密类型。

        +----+---------------------+
        | 值 | 含义                |
        +----+---------------------+
        | 0  | 公开频道            |
        +----+---------------------+
        | 1  | 群主管理员可见      |
        +----+---------------------+
        | 2  | 群主管理员+指定成员 |
        +----+---------------------+

    position: :class:`int`
        在类别列表中的位置。 这是一个从 0 开始的数字。例如顶部频道是位置 0。
    """

    __slots__ = ('name', 'id', 'guild', '_state', 'position', 'category_id', 'private_type')

    def __init__(self, *, state: ConnectionState, guild: Guild, data: CategoryChannelPayload):
        self._state: ConnectionState = state
        self.id: int = int(data['id'])
        self._update(guild, data)

    def __repr__(self) -> str:
        return f'<CategoryChannel id={self.id} name={self.name!r} position={self.position}>'

    def _update(self, guild: Guild, data: CategoryChannelPayload) -> None:
        self.guild: Guild = guild
        self.name: str = data['name']
        self.category_id: Optional[int] = int(data.get('parent_id'))
        self.position: int = data['position']
        self.private_type: int = data.get('private_type')

    @property
    def _sorting_bucket(self) -> int:
        return ChannelType.category.value

    @property
    def type(self) -> ChannelType:
        """:class:`ChannelType`: 频道的 QQ 类型。"""
        return ChannelType.category

    @property
    def channels(self) -> List[GuildChannelType]:
        def comparator(channel):
            return not isinstance(channel, TextChannel), channel.position

        ret = [c for c in self.guild.channels if c.category_id == self.id]
        ret.sort(key=comparator)
        return ret

    @property
    def text_channels(self) -> List[TextChannel]:
        ret = [c for c in self.guild.channels if c.category_id == self.id and isinstance(c, TextChannel)]
        ret.sort(key=lambda c: (c.position, c.id))
        return ret

    @property
    def voice_channels(self) -> List[VoiceChannel]:
        ret = [c for c in self.guild.channels if c.category_id == self.id and isinstance(c, VoiceChannel)]
        ret.sort(key=lambda c: (c.position, c.id))
        return ret

    @property
    def live_channels(self) -> List[LiveChannel]:
        ret = [c for c in self.guild.channels if c.category_id == self.id and isinstance(c, LiveChannel)]
        ret.sort(key=lambda c: (c.position, c.id))
        return ret

    @property
    def app_channels(self) -> List[AppChannel]:
        ret = [c for c in self.guild.channels if c.category_id == self.id and isinstance(c, AppChannel)]
        ret.sort(key=lambda c: (c.position, c.id))
        return ret

    @property
    def thread_channels(self) -> List[ThreadChannel]:
        ret = [c for c in self.guild.channels if c.category_id == self.id and isinstance(c, ThreadChannel)]
        ret.sort(key=lambda c: (c.position, c.id))
        return ret


class PartialMessageable(abc.Messageable, Hashable):
    def __init__(self, state: ConnectionState, id: int, type: Optional[ChannelType] = None):
        self._state: ConnectionState = state
        self._channel: Object = Object(id=id)
        self.id: int = id
        self.type: Optional[ChannelType] = type

    async def _get_channel(self) -> Object:
        return self._channel

    def get_partial_message(self, message_id: int, /) -> PartialMessage:
        from .message import PartialMessage

        return PartialMessage(channel=self, id=message_id)


def _guild_channel_factory(channel_type: int):
    value = try_enum(ChannelType, channel_type)
    if value is ChannelType.text:
        return TextChannel, value
    elif value is ChannelType.voice:
        return VoiceChannel, value
    elif value is ChannelType.category:
        return CategoryChannel, value
    elif value is ChannelType.live:
        return LiveChannel, value
    elif value is ChannelType.app:
        return AppChannel, value
    elif value is ChannelType.thread:
        return ThreadChannel, value
    else:
        return None, value


def _channel_factory(channel_type: int):
    cls, value = _guild_channel_factory(channel_type)
    return cls, value
