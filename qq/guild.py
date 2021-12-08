from __future__ import annotations

from typing import (
    Dict,
    List,
    Union, Optional, Tuple, TYPE_CHECKING,
)

from .channel import _guild_channel_factory, TextChannel, CategoryChannel, AppChannel, LiveChannel, ThreadChannel
from .member import Member
from .role import Role
from .types.guild import Guild as GuildPayload
from .types.channel import VoiceChannel

if TYPE_CHECKING:
    from .state import ConnectionState

GuildChannel = Union[VoiceChannel, TextChannel, CategoryChannel, AppChannel, LiveChannel, ThreadChannel]
VocalGuildChannel = Union[VoiceChannel]
ByCategoryItem = Tuple[Optional[CategoryChannel], List[GuildChannel]]


class Guild:
    __slots__ = (
        'id',
        'name',
        'icon',
        'owner_id',
        'owner',
        '_member_count',
        'max_members',
        'description',
        'joined_at',
        '_channels',
        '_members',
        '_roles',
        '_state',
        '_large',
        'unavailable'
    )

    def __init__(self, data: GuildPayload, state: ConnectionState):
        self._channels: Dict[int, GuildChannel] = {}
        self._state: ConnectionState = state
        self._from_data(data)

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
        self._member_count = guild.get('member_count')
        self.max_members = guild.get('max_members')
        self.description = guild.get('description')
        self.joined_at = guild.get('joined_at')
        self.unavailable: bool = guild.get('unavailable', False)
        self._roles: Dict[int, Role] = {}
        state = self._state  # speed up attribute access
        self._large: Optional[bool] = None if self._member_count is None else self._member_count >= 250
        for r in guild.get('roles', []):
            role = Role(guild=self, data=r, state=state)
            self._roles[role.id] = role
        self._sync()

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
        channels, roles = self._state.http.sync_guild_channels_roles(self.id)
        for r in roles:
            role = Role(guild=self, data=r, state=self._state)
            self._roles[role.id] = role
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

    @property
    def large(self) -> bool:
        if self._large is None:
            try:
                return self._member_count >= 250
            except AttributeError:
                return len(self._members) >= 250
        return self._large

    @property
    def me(self) -> Member:
        self_id = self._state.user.id
        # The self member is *always* cached
        return self.get_member(self_id)  # type: ignore

    @property
    def text_channels(self) -> List[TextChannel]:
        r = [ch for ch in self._channels.values() if isinstance(ch, TextChannel)]
        r.sort(key=lambda c: (c.position, c.id))
        return r

    @property
    def categories(self) -> List[CategoryChannel]:
        r = [ch for ch in self._channels.values() if isinstance(ch, CategoryChannel)]
        r.sort(key=lambda c: (c.position, c.id))
        return r

    def by_category(self) -> List[ByCategoryItem]:
        grouped: Dict[Optional[int], List[GuildChannel]] = {}
        for channel in self._channels.values():
            if isinstance(channel, CategoryChannel):
                grouped.setdefault(channel.id, [])
                continue

            try:
                grouped[channel.category_id].append(channel)
            except KeyError:
                grouped[channel.category_id] = [channel]

        def key(t: ByCategoryItem) -> Tuple[Tuple[int, int], List[GuildChannel]]:
            k, v = t
            return (k.position, k.id) if k else (-1, -1), v

        _get = self._channels.get
        as_list: List[ByCategoryItem] = [(_get(k), v) for k, v in grouped.items()]  # type: ignore
        as_list.sort(key=key)
        for _, channels in as_list:
            channels.sort(key=lambda c: (c._sorting_bucket, c.position, c.id))
        return as_list

    def _resolve_channel(self, id: Optional[int], /) -> Optional[Union[GuildChannel, ]]:
        if id is None:
            return

        return self._channels.get(id)

    def get_channel(self, channel_id: int, /) -> Optional[GuildChannel]:
        return self._channels.get(channel_id)

    def get_member(self, user_id: int, /) -> Optional[Member]:
        return self._members.get(user_id)

    @property
    def roles(self) -> List[Role]:
        return sorted(self._roles.values())

    def _add_member(self, member: Member, /) -> None:
        self._members[member.id] = member

    @property
    def chunked(self) -> bool:
        count = getattr(self, '_member_count', None)
        if count is None:
            return False
        return count == len(self._members)


