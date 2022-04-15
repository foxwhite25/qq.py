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

from typing import Any, TYPE_CHECKING, Optional, Type, TypeVar, Dict, List

from .abc import *
from .asset import Asset

if TYPE_CHECKING:
    from .channel import DMChannel
    from .guild import Guild
    from .message import Message
    from .state import ConnectionState

    from .types.channel import DMChannel as DMChannelPayload
    from .types.user import User as UserPayload

__all__ = (
    'User',
    'ClientUser',
)

BU = TypeVar('BU', bound='BaseUser')


class _UserTag:
    __slots__ = ()
    id: int


class BaseUser(_UserTag):
    __slots__ = (
        'name',
        'id',
        '_avatar',
        'bot',
        '_state',
    )

    if TYPE_CHECKING:
        name: str
        id: int
        bot: bool
        _state: ConnectionState
        _avatar: Optional[Asset]

    def __init__(self, *, state: ConnectionState, data: UserPayload) -> None:
        self._state = state
        self._avatar = Asset._from_avatar(state=self._state, avatar=data.get('avatar', ''))
        self._update(data)

    def __repr__(self) -> str:
        return (
            f"<BaseUser id={self.id} name={self.name!r} bot={self.bot}>"
        )

    def __str__(self) -> str:
        return f'{self.name}'

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, _UserTag) and other.id == self.id

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return self.id >> 22

    def _update(self, data: UserPayload) -> None:
        self.name = data['username']
        self.id = int(data['id'])
        if 'avatar' in data:
            self._avatar = data['avatar']
        self.bot = data.get('bot', False)

    @classmethod
    def _copy(cls: Type[BU], user: BU) -> BU:
        self = cls.__new__(cls)  # bypass __init__

        self.name = user.name
        self.id = user.id
        self._avatar = user._avatar
        self.bot = user.bot
        self._state = user._state

        return self

    def _to_minimal_user_json(self) -> Dict[str, Any]:
        return {
            'username': self.name,
            'id': self.id,
            'avatar': self._avatar,
            'bot': self.bot,
        }

    @property
    def avatar(self) -> Optional[Asset]:
        """Optional[:class:`Asset`]: 返回用户拥有的头像的 :class:`Asset`。
        如果用户没有传统头像，则返回 ``None``。
        如果你想要用户显示的头像，请考虑 :attr:`display_avatar`。
        """
        if self._avatar is not None:
            return Asset._from_avatar(self._state, self._avatar)
        return None

    @property
    def display_avatar(self) -> Asset:
        """:class:`Asset`: 返回用户的显示头像。
        对于普通用户，这只是他们的默认头像或上传的头像。
        """
        return self.avatar

    @property
    def mention(self) -> str:
        """:class:`str`: 返回一个字符串，允许你提及给定的用户。"""
        return f'<@!{self.id}>'

    @property
    def display_name(self) -> str:
        """:class:`str`: 返回用户的显示名称。
        对于普通用户，这只是他们的用户名，但如果他们有频道特定的昵称，则返回该昵称。
        """
        return self.name

    def mentioned_in(self, message: Message) -> bool:
        """检查用户是否在指定的消息中被提及。
        
        Parameters
        -----------
        message: :class:`Message`
            用于检查是否被提及的消息。
            
        Returns
        -------
        :class:`bool`
            指示消息中是否提到了用户。
        """

        if message.mention_everyone:
            return True

        return any(user.id == self.id for user in message.mentions)


class ClientUser(BaseUser):
    """代表你的 QQ 用户。

    .. container:: operations

        .. describe:: x == y

            检查两个用户是否相等。

        .. describe:: x != y

            检查两个用户是否不相等。

        .. describe:: hash(x)

            返回用户的哈希值。

        .. describe:: str(x)

            返回用户名。

    Attributes
    -----------
    name: :class:`str`
        用户的用户名。
    id: :class:`int`
        用户的唯一 ID。
    bot: :class:`bool`
        指定用户是否为机器人帐户。
    """

    def __init__(self, *, state: ConnectionState, data: UserPayload) -> None:
        super().__init__(state=state, data=data)

    def __repr__(self) -> str:
        return (
            f'<ClientUser id={self.id} name={self.name!r} bot={self.bot}>'
        )

    def _update(self, data: UserPayload) -> None:
        super()._update(data)


class User(BaseUser, Messageable):
    """代表一个 QQ 用户。

    .. container:: operations

        .. describe:: x == y

            检查两个用户是否相等。

        .. describe:: x != y

            检查两个用户是否不相等。

        .. describe:: hash(x)

            返回用户的哈希值。

        .. describe:: str(x)

            返回用户名。

    Attributes
    -----------
    name: :class:`str`
        用户的用户名。
    id: :class:`int`
        用户的唯一 ID。
    bot: :class:`bool`
        指定用户是否为机器人帐户。
    """

    __slots__ = ('_stored',)

    def __init__(self, *, state: ConnectionState, data: UserPayload) -> None:
        super().__init__(state=state, data=data)
        self._stored: bool = False

    def __repr__(self) -> str:
        return f'<User id={self.id} name={self.name!r} bot={self.bot}>'

    def __del__(self) -> None:
        try:
            if self._stored:
                self._state.deref_user(self.id)
        except Exception:
            pass

    @classmethod
    def _copy(cls, user):
        self = super()._copy(user)
        self._stored = False
        return self

    @property
    def dm_channel(self) -> Optional[DMChannel]:
        """Optional[:class:`DMChannel`]: 如果存在，则返回与此用户关联的子频道。
        如果返回 ``None`` ，您可以通过调用 :meth:`create_dm` 协程函数来创建私信子频道。
        """
        return self._state._get_private_channel_by_user(self.id)

    @property
    def mutual_guilds(self) -> List[Guild]:
        """List[:class:`Guild`]: 用户与客户端共同的频道。

        .. note::

            这只会返回客户端内部缓存中的共同频道。

        """
        return [guild for guild in self._state._guilds.values() if guild.get_member(self.id)]

    async def create_dm(self, guild: Guild) -> DMChannel:
        """|coro|
        用这个用户创建一个 :class:`.DMChannel`。
        这应该很少被调用，因为这对大多数人来说都不需要用到的。

        Parameters
        -----------
        guild: :class: `~qq.Guild`
            用于创建私信的源频道

        Returns
        -------
        :class:`.DMChannel`
            创建的频道。
        """
        found = self.dm_channel
        if found is not None:
            return found

        state = self._state
        data: DMChannelPayload = await state.http.start_private_message(self.id, guild.id)
        return state.add_dm_channel(data, recipients=self)
