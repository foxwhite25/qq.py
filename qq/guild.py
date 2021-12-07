from typing import (
    Dict,
    List,
    Union, Optional,
)

from .abc import GuildChannel
from .member import Member
from .role import Role
from .state import ConnectionState
from .types.guild import Guild as GuildPayload
from .types.channel import VoiceChannel, TextChannel, CategoryChannel

VocalGuildChannel = Union[VoiceChannel]

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
        '_members',
        '_roles',
        '_state'
    )

    def __init__(self, data: GuildPayload, channels: List[GuildChannel], state: ConnectionState):
        self._channels: Dict[int, GuildChannel] = {}
        self._state: ConnectionState = state
        self._from_data(data)
        self._sync(channels)

    def _add_role(self, role: Role, /) -> None:
        self._roles[role.id] = role

    def _remove_role(self, role_id: int, /) -> Role:
        # this raises KeyError if it fails..
        role = self._roles.pop(role_id)
        return role

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
        self._roles: Dict[int, Role] = {}
        state = self._state  # speed up attribute access
        for r in guild.get('roles', []):
            role = Role(guild=self, data=r, state=state)
            self._roles[role.id] = role

    def _add_channel(self, channel: GuildChannel, /) -> None:
        self._channels[channel.id] = channel

    def _remove_channel(self, channel: GuildChannel, /) -> None:
        self._channels.pop(channel.id, None)

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
        return list(self._channels.values())

    @property
    def members(self) -> List[Member]:
        """List[:class:`Member`]: A list of members that belong to this guild."""
        return list(self._members.values())

    def get_role(self, role_id: int, /) -> Optional[Role]:
        return self._roles.get(role_id)
