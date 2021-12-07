from __future__ import annotations

from typing import (
    Dict,
    List,
    Union, Optional,
)

from .channel import _guild_channel_factory, TextChannel, CategoryChannel, AppChannel, LiveChannel, ThreadChannel
from .member import Member
from .role import Role
from .state import ConnectionState
from .types.guild import Guild as GuildPayload
from .types.channel import VoiceChannel

GuildChannel = Union[VoiceChannel, TextChannel, CategoryChannel, AppChannel, LiveChannel, ThreadChannel]
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

    def __init__(self, data: GuildPayload, state: ConnectionState):
        self._channels: Dict[int, GuildChannel] = {}
        self._state: ConnectionState = state
        self._from_data(data)
        self._sync()

    def _add_role(self, role: Role, /) -> None:
        self._roles[role.id] = role

    def _remove_role(self, role_id: int, /) -> Role:
        # this raises KeyError if it fails.
        role = self._roles.pop(role_id)
        return role

    def _from_data(self, guild: GuildPayload) -> None:
        self.id = int(guild.get('id'))
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

    def _sync(self) -> None:
        # I know it's jank to put a sync requests here,
        # but QQ just does not give all the info about guilds unless you requests it
        channels = self._state.http.sync_guild_channels(self.id)
        for c in channels:
            factory, ch_type = _guild_channel_factory(c['type'])
            if factory:
                self._add_channel(factory(guild=self, data=c, state=self._state))  # type: ignore

    @property
    def channels(self) -> List[GuildChannel]:
        return list(self._channels.values())

    @property
    def members(self) -> List[Member]:
        """List[:class:`Member`]: A list of members that belong to this guild."""
        return list(self._members.values())

    def get_role(self, role_id: int, /) -> Optional[Role]:
        return self._roles.get(role_id)
