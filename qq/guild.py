from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    NamedTuple,
    Sequence,
    Set,
    Literal,
    Optional,
    TYPE_CHECKING,
    Tuple,
    Union,
    overload,
)


from .types.guild import Guild as GuildPayload
from .types.channel import VoiceChannel, TextChannel, CategoryChannel

VocalGuildChannel = Union[VoiceChannel]
GuildChannel = Union[VoiceChannel, TextChannel, CategoryChannel]


class Guild:
    __slots__ = (
        'id',
        'name',
        'icon',
        'owner_id',
        'owner',
        'member_count',
        'max_members',
        'description',
        'joined_at',
        '_channels',
        '_members'
    )

    def __init__(self, data: GuildPayload, channels: List[GuildChannel]):
        self._channels: Dict[int, GuildChannel] = {}
        self._from_data(data)
        self._sync(channels)

    def _from_data(self, guild: GuildPayload) -> None:
        print(guild)
        self.id = guild.get('id')
        self.name = guild.get('name')
        self.icon = guild.get('icon')
        self.owner_id = guild.get('owner_id')
        self.owner = guild.get('owner')
        self.member_count = guild.get('member_count')
        self.max_members = guild.get('max_members')
        self.description = guild.get('description')
        self.joined_at = guild.get('joined_at')

    def _add_channel(self, channel: GuildChannel, /) -> None:
        self._channels[channel.get('id')] = channel

    def _remove_channel(self, channel: GuildChannel, /) -> None:
        self._channels.pop(channel.get('id'), None)

    def __str__(self) -> str:
        return self.name or ''

    def __repr__(self) -> str:
        attrs = (
            ('id', self.id),
            ('name', self.name),
            ('member_count', getattr(self, '_member_count', None)),
        )
        inner = ' '.join('%s=%r' % t for t in attrs)
        return f'<Guild {inner}>'

    def _sync(self, channels: List[GuildChannel]) -> None:
        for c in channels:
            self._add_channel(c)  # type: ignore

    @property
    def channels(self) -> List[GuildChannel]:
        """List[:class:`abc.GuildChannel`]: A list of channels that belongs to this guild."""
        return list(self._channels.values())


