from __future__ import annotations

from typing import Any, TYPE_CHECKING, Optional, Type, TypeVar, Dict, List

from .abc import *

if TYPE_CHECKING:
    from .asset import Asset
    from .guild import Guild
    from .colour import Colour
    from .message import Message
    from .state import ConnectionState
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
        _avatar: Optional[str]

    def __init__(self, *, state: ConnectionState, data: UserPayload) -> None:
        self._state = state
        self._avatar = None
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
        """Optional[:class:`Asset`]: Returns an :class:`Asset` for the avatar the user has.
        If the user does not have a traditional avatar, ``None`` is returned.
        If you want the avatar that a user has displayed, consider :attr:`display_avatar`.
        """
        if self._avatar is not None:
            return Asset._from_avatar(self._state, self._avatar)
        return None

    @property
    def display_avatar(self) -> Asset:
        """:class:`Asset`: Returns the user's display avatar.
        For regular users this is just their default avatar or uploaded avatar.
        .. versionadded:: 2.0
        """
        return self.avatar

    @property
    def colour(self) -> Colour:
        """:class:`Colour`: A property that returns a colour denoting the rendered colour
        for the user. This always returns :meth:`Colour.default`.
        There is an alias for this named :attr:`color`.
        """
        return Colour.default()

    @property
    def color(self) -> Colour:
        """:class:`Colour`: A property that returns a color denoting the rendered color
        for the user. This always returns :meth:`Colour.default`.
        There is an alias for this named :attr:`colour`.
        """
        return self.colour

    @property
    def mention(self) -> str:
        """:class:`str`: Returns a string that allows you to mention the given user."""
        return f'<@{self.id}>'

    @property
    def display_name(self) -> str:
        """:class:`str`: Returns the user's display name.
        For regular users this is just their username, but
        if they have a guild specific nickname then that
        is returned instead.
        """
        return self.name

    def mentioned_in(self, message: Message) -> bool:
        """Checks if the user is mentioned in the specified message.
        Parameters
        -----------
        message: :class:`Message`
            The message to check if you're mentioned in.
        Returns
        -------
        :class:`bool`
            Indicates if the user is mentioned in the message.
        """

        if message.mention_everyone:
            return True

        return any(user.id == self.id for user in message.mentions)


class ClientUser(BaseUser):
    def __init__(self, *, state: ConnectionState, data: UserPayload) -> None:
        super().__init__(state=state, data=data)

    def __repr__(self) -> str:
        return (
            f'<ClientUser id={self.id} name={self.name!r} bot={self.bot}>'
        )

    def _update(self, data: UserPayload) -> None:
        super()._update(data)


class User(BaseUser, Messageable):
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
    def mutual_guilds(self) -> List[Guild]:
        """List[:class:`Guild`]: The guilds that the user shares with the client.
        .. note::
            This will only return mutual guilds within the client's internal cache.
        .. versionadded:: 1.7
        """
        return [guild for guild in self._state._guilds.values() if guild.get_member(self.id)]
