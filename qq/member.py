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

import datetime
import inspect
import itertools
from operator import attrgetter
from typing import TypeVar, TYPE_CHECKING, Optional, List, Tuple, Any, Type, Literal, Union

from . import utils
from .abc import Messageable
from .colour import Colour
from .object import Object
from .user import _UserTag, BaseUser, User

if TYPE_CHECKING:
    from .abc import GuildChannel
    from .guild import Guild
    from .asset import Asset
    from .message import Message
    from .state import ConnectionState
    from .types.member import (
        MemberWithUser as MemberWithUserPayload,
        Member as MemberPayload,
        UserWithMember as UserWithMemberPayload,
    )
    from .types.user import User as UserPayload
    from .role import Role

__all__ = (
    'Member',
)


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
    """代表一个 :class:`Guild` 的 QQ 成员。这实现了 :class:`User` 的很多功能。

    .. container:: operations

        .. describe:: x == y

            检查两个成员是否相等。
            请注意，这也适用于 :class:`User` 实例。

        .. describe:: x != y

            检查两个成员是否不相等。
            请注意，这也适用于 :class:`User` 实例。

        .. describe:: hash(x)

            返回成员的哈希值。

        .. describe:: str(x)

            返回成员的名称。

    Attributes
    ----------
    joined_at: Optional[:class:`datetime.datetime`]
        一个 datetime 对象，它指定成员加入频道的日期和时间。
        如果成员离开并重新加入频道，这将是最新的日期。在某些情况下，这可以是 ``None`` 。
    guild: :class:`Guild`
        成员所属的频道。
    nick: Optional[:class:`str`]
        用户的频道特定昵称。
    """

    __slots__ = (
        '_roles',
        'joined_at',
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
        self._roles: utils.SnowflakeList = utils.SnowflakeList(map(int, data['roles'])) \
            if 'roles' in data and 'Normal' not in data['roles'] else utils.SnowflakeList(map(int, []))

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
        # self.nick = data.get('nick', None)

    @classmethod
    def _try_upgrade(cls: Type[M], *, data: UserWithMemberPayload, guild: Guild, state: ConnectionState) -> Union[
        User, M]:
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
        self.guild = member.guild
        self.nick = member.nick
        self._state = member._state
        self._avatar = member._avatar

        # Reference will not be copied unless necessary by PRESENCE_UPDATE
        # See below
        self._user = member._user
        return self

    async def _get_channel(self):
        if isinstance(self.guild, Object):
            ch = self.guild.channels[0]
        else:
            ch = await self.create_dm(self.guild)
        return ch, True

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
        """:class:`Colour`: 返回颜色的 property，该颜色表示成员的呈现颜色。
        如果默认颜色是渲染的颜色，则返回一个 :meth:`Colour.default` 实例。
        这个 property 有一个别名:attr:`color`。
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
        """:class:`Colour`: 返回颜色的 property，该颜色表示成员的呈现颜色。
        如果默认颜色是渲染的颜色，则返回一个 :meth:`Colour.default` 实例。
        这个 property 有一个别名:attr:`colour`。
        """
        return self.colour

    @property
    def roles(self) -> List[Role]:
        """List[:class:`Role`]: 成员所属的 :class:`Role` 的 :class:`list` 。
        """
        result = []
        g = self.guild
        for role_id in self._roles:
            role = g.get_role(role_id)
            if role:
                result.append(role)
        result.sort()
        return result

    @property
    def mention(self) -> str:
        """:class:`str`: 返回一个字符串，允许你提及该成员。"""
        return f'<@{self._user.id}>'

    @property
    def display_name(self) -> str:
        """:class:`str`: 返回用户的显示名称。
        对于普通用户，这只是他们的用户名，但如果他们有频道特定的昵称，则返回该昵称。
        """
        return self.nick or self.name

    @property
    def display_avatar(self) -> Asset:
        """:class:`Asset`: 返回成员的显示头像。
        """
        return self._user.avatar

    def mentioned_in(self, message: Message) -> bool:
        """检查指定消息中是否提及该成员。

        Parameters
        -----------
        message: :class:`Message`
            用于检查是否被提及的消息。

        Returns
        -------
        :class:`bool`
            指示消息中是否提及该成员。
        """
        if message.guild is None or message.guild.id != self.guild.id:
            return False

        if self._user.mentioned_in(message):
            return True

        return any(self._roles.has(role.id) for role in message.role_mentions)

    async def add_roles(
            self, *roles: Role,
            reason: Optional[str] = None,
            atomic: bool = True,
            channel: GuildChannel = None
    ) -> None:
        r"""|coro|
        给成员一些 :class:`Role` 。

        Parameters
        -----------
        \*roles: :class:`Role`
            一个给成员的 :class:`Role` 。
        reason: Optional[:class:`str`]
            添加这些身份组的原因。
        atomic: :class:`bool`
            是否以 atomic 方式添加身份组。这将确保无论缓存的当前状态如何，都将始终应用多个操作。
        channel: Optional[:class: `abc.GuildChannel`]
            仅在添加身份组为 5 (子频道管理员) 的时候需要

        Raises
        -------
        Forbidden
            你无权添加这些身份组。
        HTTPException
            添加身份组失败。
        """

        if not atomic:
            new_roles = utils._unique(Object(id=r.id) for s in (self.roles[1:], roles) for r in s)
            await self.edit(roles=new_roles, reason=reason)
        else:
            req = self._state.http.add_role
            guild_id = self.guild.id
            user_id = self.id
            for role in roles:
                await req(guild_id, user_id, role.id, channel.id, reason=reason)

    async def remove_roles(
            self, *roles: Role,
            channel: Optional[GuildChannel] = None,
            reason: Optional[str] = None,
            atomic: bool = True
    ) -> None:
        r"""|coro|
        从此成员中删除一些 :class:`Role` 。

        Parameters
        -----------
        \*roles: :class:`Role`
            一个给成员的 :class:`Role` 。
        reason: Optional[:class:`str`]
            删除这些身份组的原因。 
        atomic: :class:`bool`
            是否以 atomic 方式删除身份组。这将确保无论缓存的当前状态如何，都将始终应用多个操作。
        channel: Optional[:class: `abc.GuildChannel`]
            仅在添加身份组为 5 (子频道管理员) 的时候需要

        Raises
        -------
        Forbidden
            你无权删除这些身份组。
        HTTPException
            删除身份组失败。
        """

        if not atomic:
            new_roles = [Object(id=r.id) for r in self.roles[1:]]  # remove @everyone
            for role in roles:
                try:
                    new_roles.remove(Object(id=role.id))
                except ValueError:
                    pass

            await self.edit(roles=new_roles, reason=reason)
        else:
            req = self._state.http.remove_role
            guild_id = self.guild.id
            user_id = self.id
            for role in roles:
                await req(guild_id, user_id, role.id, channel.id, reason=reason)

    def get_role(self, role_id: int, /) -> Optional[Role]:
        return self.guild.get_role(role_id) if self._roles.has(role_id) else None

    async def unmute(
            self,
            *,
            reason: Optional[str] = None,
    ) -> None:
        """|coro|
        禁言这个用户，相当于 :meth:`Guild.unmute_member` 。
        """
        await self.guild.unmute_member(self, reason=reason)

    async def mute(
            self,
            duration: Union[datetime.datetime, int] = 10,
            *,
            reason: Optional[str] = None,
    ) -> None:
        """|coro|
        禁言这个用户，相当于 :meth:`Guild.mute_member` 。
        """
        await self.guild.mute_member(self, duration=duration, reason=reason)

    async def kick(self, *, reason: Optional[str] = None) -> None:
        """|coro|
        踢出这个成员。 与 :meth:`Guild.kick` 相似。
        """
        await self.guild.kick(self, reason=reason)

    async def ban(
            self,
            *,
            delete_message_days: Literal[0, 1, 2, 3, 4, 5, 6, 7] = 1,
            reason: Optional[str] = None,
    ) -> None:
        """|coro|
        封禁这个用户。 与 :meth:`Guild.ban` 相似。
        """
        await self.guild.ban(self, reason=reason, delete_message_days=delete_message_days)
