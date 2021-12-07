from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, Optional, List

from . import abc
from .enum import ChannelType, try_enum
from .mixins import Hashable
from .object import Object

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
    __slots__ = (
        'name',
        'id',
        'guild',
        '_state',
        'category_id',
        'position',
        '_type',
    )

    def __init__(self, *, state: ConnectionState, guild: Guild, data: TextChannelPayload):
        self._state: ConnectionState = state
        self.id: int = int(data['id'])
        self._type: int = data['type']
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
        return [m for m in self.guild.members]

    def get_partial_message(self, message_id: int, /) -> PartialMessage:
        from .message import PartialMessage

        return PartialMessage(channel=self, id=message_id)


class VoiceChannel(abc.GuildChannel, Hashable):
    __slots__ = (
        'name',
        'id',
        'guild',
        '_state',
        'position',
        'category_id',
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

    def __repr__(self) -> str:
        attrs = [
            ('id', self.id),
            ('name', self.name),
            ('position', self.position),
            ('category_id', self.category_id),
        ]
        joined = ' '.join('%s=%r' % t for t in attrs)
        return f'<{self.__class__.__name__} {joined}>'


class LiveChannel(abc.GuildChannel, Hashable):
    __slots__ = (
        'name',
        'id',
        'guild',
        '_state',
        'position',
        'category_id',
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
    __slots__ = (
        'name',
        'id',
        'guild',
        '_state',
        'position',
        'category_id',
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
    __slots__ = (
        'name',
        'id',
        'guild',
        '_state',
        'position',
        'category_id',
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
    __slots__ = ('name', 'id', 'guild', '_state', 'position', 'category_id')

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

    @property
    def _sorting_bucket(self) -> int:
        return ChannelType.category.value

    @property
    def type(self) -> ChannelType:
        """:class:`ChannelType`: The channel's Discord type."""
        return ChannelType.category

    def is_nsfw(self) -> bool:
        """:class:`bool`: Checks if the category is NSFW."""
        return self.nsfw

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
