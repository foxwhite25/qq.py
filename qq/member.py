from __future__ import annotations

import datetime
import inspect
import itertools
from operator import attrgetter
from typing import TypeVar, TYPE_CHECKING, Optional, List, Dict, Tuple, Any, Type, Literal, Union

from . import utils
from .user import _UserTag, BaseUser, User
from .abc import Messageable

if TYPE_CHECKING:
    from .guild import Guild
    from .asset import Asset
    from .colour import Colour
    from .message import Message
    from .object import Object
    from .state import ConnectionState
    from .user import *
    from .types.member import (
        MemberWithUser as MemberWithUserPayload,
        Member as MemberPayload,
        UserWithMember as UserWithMemberPayload,
    )
    from .types.user import User as UserPayload
    from .role import Role


def flatten_user(cls):
    for attr, value in itertools.chain(BaseUser.__dict__.items(), User.__dict__.items()):
        # ignore private/special methods
        if attr.startswith('_'):
            continue

        # don't override what we already have
        if attr in cls.__dict__:
            continue

        # if it's a slotted attribute or a property, redirect it
        # slotted members are implemented as member_descriptors in Type.__dict__
        if not hasattr(value, '__annotations__'):
            getter = attrgetter('_user.' + attr)
            setattr(cls, attr, property(getter, doc=f'Equivalent to :attr:`User.{attr}`'))
        else:
            # Technically, this can also use attrgetter
            # However I'm not sure how I feel about "functions" returning properties
            # It probably breaks something in Sphinx.
            # probably a member function by now
            def generate_function(x):
                # We want sphinx to properly show coroutine functions as coroutines
                if inspect.iscoroutinefunction(value):

                    async def general(self, *args, **kwargs):  # type: ignore
                        return await getattr(self._user, x)(*args, **kwargs)

                else:

                    def general(self, *args, **kwargs):
                        return getattr(self._user, x)(*args, **kwargs)

                general.__name__ = x
                return general

            func = generate_function(attr)
            func = utils.copy_doc(value)(func)
            setattr(cls, attr, func)

    return cls


M = TypeVar('M', bound='Member')


@flatten_user
class Member(Messageable, _UserTag):
    __slots__ = (
        '_roles',
        'joined_at',
        'premium_since',
        'activities',
        'guild',
        'nick',
        '_user',
        '_state',
        '_avatar',
    )

    if TYPE_CHECKING:
        name: str
        id: int
        bot: bool
        avatar: Optional[Asset]
        mutual_guilds: List[Guild]

    def __init__(self, *, data: MemberWithUserPayload, guild: Guild, state: ConnectionState):
        self._state: ConnectionState = state
        self._user: User = state.store_user(data['user'])
        self.guild: Guild = guild
        self.joined_at: Optional[datetime.datetime] = utils.parse_time(data.get('joined_at'))
        self._roles: utils.SnowflakeList = utils.SnowflakeList(map(int, data['roles']))

        self.nick: Optional[str] = data.get('nick', None)
        self._avatar: Optional[str] = data.get('avatar')

    def __str__(self) -> str:
        return str(self._user)

    def __repr__(self) -> str:
        return (
            f'<Member id={self._user.id} name={self._user.name!r} bot={self._user.bot} '
            f'nick={self.nick!r} guild={self.guild!r}>'
        )

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, _UserTag) and other.id == self.id

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash(self._user)

    @classmethod
    def _from_message(cls: Type[M], *, message: Message, data: MemberPayload) -> M:
        author = message.author
        data['user'] = author._to_minimal_user_json()  # type: ignore
        return cls(data=data, guild=message.guild, state=message._state)  # type: ignore

    def _update_from_message(self, data: MemberPayload) -> None:
        self.joined_at = utils.parse_time(data.get('joined_at'))
        self.nick = data.get('nick', None)

    @classmethod
    def _try_upgrade(cls: Type[M], *, data: UserWithMemberPayload, guild: Guild, state: ConnectionState) -> Union[User, M]:
        # A User object with a 'member' key
        try:
            member_data = data.pop('member')
        except KeyError:
            return state.create_user(data)
        else:
            member_data['user'] = data  # type: ignore
            return cls(data=member_data, guild=guild, state=state)  # type: ignore

    @classmethod
    def _copy(cls: Type[M], member: M) -> M:
        self: M = cls.__new__(cls)  # to bypass __init__

        self._roles = member._roles
        self.joined_at = member.joined_at
        self.premium_since = member.premium_since
        self._client_status = member._client_status.copy()
        self.guild = member.guild
        self.nick = member.nick
        self.pending = member.pending
        self.activities = member.activities
        self._state = member._state
        self._avatar = member._avatar

        # Reference will not be copied unless necessary by PRESENCE_UPDATE
        # See below
        self._user = member._user
        return self

    async def _get_channel(self):
        ch = await self.create_dm()
        return ch

    def _update(self, data: MemberPayload) -> None:
        # the nickname change is optional,
        # if it isn't in the payload then it didn't change
        try:
            self.nick = data['nick']
        except KeyError:
            pass

    def _update_inner_user(self, user: UserPayload) -> Optional[Tuple[User, User]]:
        u = self._user
        original = (u.name, u._avatar)
        # These keys seem to always be available
        modified = (user['username'], user['avatar'])
        if original != modified:
            to_return = User._copy(self._user)
            u.name, u._avatar = modified
            # Signal to dispatch on_user_update
            return to_return, u

    @property
    def colour(self) -> Colour:
        """:class:`Colour`: A property that returns a colour denoting the rendered colour
        for the member. If the default colour is the one rendered then an instance
        of :meth:`Colour.default` is returned.
        There is an alias for this named :attr:`color`.
        """

        roles = self.roles[1:]  # remove @everyone

        # highest order of the colour is the one that gets rendered.
        # if the highest is the default colour then the next one with a colour
        # is chosen instead
        for role in reversed(roles):
            if role.colour.value:
                return role.colour
        return Colour.default()

    @property
    def color(self) -> Colour:
        """:class:`Colour`: A property that returns a color denoting the rendered color for
        the member. If the default color is the one rendered then an instance of :meth:`Colour.default`
        is returned.
        There is an alias for this named :attr:`colour`.
        """
        return self.colour

    @property
    def roles(self) -> List[Role]:
        """List[:class:`Role`]: A :class:`list` of :class:`Role` that the member belongs to. Note
        that the first element of this list is always the default '@everyone'
        role.
        These roles are sorted by their position in the role hierarchy.
        """
        result = []
        g = self.guild
        for role_id in self._roles:
            role = g.get_role(role_id)
            if role:
                result.append(role)
        result.append(g.default_role)
        result.sort()
        return result

    @property
    def mention(self) -> str:
        """:class:`str`: Returns a string that allows you to mention the member."""
        return f'<@{self._user.id}>'

    @property
    def display_name(self) -> str:
        """:class:`str`: Returns the user's display name.
        For regular users this is just their username, but
        if they have a guild specific nickname then that
        is returned instead.
        """
        return self.nick or self.name

    @property
    def display_avatar(self) -> Asset:
        """:class:`Asset`: Returns the member's display avatar.
        For regular members this is just their avatar, but
        if they have a guild specific avatar then that
        is returned instead.
        .. versionadded:: 2.0
        """
        return self._user.avatar

    def mentioned_in(self, message: Message) -> bool:
        """Checks if the member is mentioned in the specified message.
        Parameters
        -----------
        message: :class:`Message`
            The message to check if you're mentioned in.
        Returns
        -------
        :class:`bool`
            Indicates if the member is mentioned in the message.
        """
        if message.guild is None or message.guild.id != self.guild.id:
            return False

        if self._user.mentioned_in(message):
            return True

        return any(self._roles.has(role.id) for role in message.role_mentions)

    @property
    def top_role(self) -> Role:
        """:class:`Role`: Returns the member's highest role.
        This is useful for figuring where a member stands in the role
        hierarchy chain.
        """
        guild = self.guild
        if len(self._roles) == 0:
            return guild.default_role

        return max(guild.get_role(rid) or guild.default_role for rid in self._roles)

    async def add_roles(self, *roles: str, reason: Optional[str] = None, atomic: bool = True) -> None:
        if not atomic:
            new_roles = utils._unique(Object(id=r.id) for s in (self.roles[1:], roles) for r in s)
            await self.edit(roles=new_roles, reason=reason)
        else:
            req = self._state.http.add_role
            guild_id = self.guild.id
            user_id = self.id
            for role in roles:
                await req(guild_id, user_id, role, reason=reason)

    async def remove_roles(self, *roles: str, reason: Optional[str] = None, atomic: bool = True) -> None:
        if not atomic:
            new_roles = [Object(id=r.id) for r in self.roles[1:]]  # remove @everyone
            for role in roles:
                try:
                    new_roles.remove(Object(id=role))
                except ValueError:
                    pass

            await self.edit(roles=new_roles, reason=reason)
        else:
            req = self._state.http.remove_role
            guild_id = self.guild.id
            user_id = self.id
            for role in roles:
                await req(guild_id, user_id, role, reason=reason)

    def get_role(self, role_id: int, /) -> Optional[Role]:
        return self.guild.get_role(role_id) if self._roles.has(role_id) else None
