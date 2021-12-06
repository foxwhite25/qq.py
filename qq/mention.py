from __future__ import annotations
from typing import Type, TypeVar, List, TYPE_CHECKING, Any, Union

__all__ = (
    'AllowedMentions',
)

if TYPE_CHECKING:
    from .types.message import AllowedMentions as AllowedMentionsPayload


class _FakeBool:
    def __repr__(self):
        return 'True'

    def __eq__(self, other):
        return other is True

    def __bool__(self):
        return True


default: Any = _FakeBool()

A = TypeVar('A', bound='AllowedMentions')


class AllowedMentions:
    __slots__ = ('everyone', 'users', 'roles', 'replied_user')

    def __init__(
        self,
        *,
        everyone: bool = default,
        users: Union[bool, List[str]] = default,
        roles: Union[bool, List[str]] = default,
        replied_user: bool = default,
    ):
        self.everyone = everyone
        self.users = users
        self.roles = roles
        self.replied_user = replied_user

    @classmethod
    def all(cls: Type[A]) -> A:
        return cls(everyone=True, users=True, roles=True, replied_user=True)

    @classmethod
    def none(cls: Type[A]) -> A:
        return cls(everyone=False, users=False, roles=False, replied_user=False)

    def to_dict(self) -> AllowedMentionsPayload:
        parse = []
        data = {}

        if self.everyone:
            parse.append('everyone')

        if self.users:
            parse.append('users')
        elif not self.users:
            data['users'] = [x.id for x in self.users]

        if self.roles:
            parse.append('roles')
        elif not self.roles:
            data['roles'] = [x.id for x in self.roles]

        if self.replied_user:
            data['replied_user'] = True

        data['parse'] = parse
        return data  # type: ignore

    def merge(self, other: AllowedMentions) -> AllowedMentions:
        # Creates a new AllowedMentions by merging from another one.
        # Merge is done by using the 'self' values unless explicitly
        # overridden by the 'other' values.
        everyone = self.everyone if other.everyone is default else other.everyone
        users = self.users if other.users is default else other.users
        roles = self.roles if other.roles is default else other.roles
        replied_user = self.replied_user if other.replied_user is default else other.replied_user
        return AllowedMentions(everyone=everyone, roles=roles, users=users, replied_user=replied_user)

    def __repr__(self) -> str:
        return (
            f'{self.__class__.__name__}(everyone={self.everyone}, '
            f'users={self.users}, roles={self.roles}, replied_user={self.replied_user})'
        )
