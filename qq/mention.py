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

from typing import Type, TypeVar, List, TYPE_CHECKING, Any, Union

__all__ = (
    'AllowedMentions',
)

if TYPE_CHECKING:
    from .types.message import AllowedMentions as AllowedMentionsPayload
    from .member import Member
    from .role import Role


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
    """一个类，表示消息中允许提及的内容。
    这个类可以在 :class:`Client` 初始化期间设置，以应用于每条发送的消息。
    它也可以通过 :meth:`abc.Messageable.send` 在每条消息的基础上应用，以获得更细粒度的控制。

    Attributes
    ------------
    everyone: :class:`bool`
        是否允许所有人和这里提到。 默认为 ``True``。
    users: Union[:class:`bool`, List[:class:`Member`]]
        控制被提及的用户。 如果为 ``True`` （默认值），则根据消息内容提及用户。
        如果 ``False`` 则根本不会提及用户。 如果给出了 :class:`Member` 的列表，则只提及所提供的用户，前提是这些用户在消息内容中。
    roles: Union[:class:`bool`, List[:class:`Role`]]
        控制提到的用户组。 如果为 ``True`` （默认值），则根据消息内容提及用户组。 如果 ``False`` 则根本不提及用户组。
        如果给出了 :class:`Role` 的列表，则只提及所提供的用户组，前提是这些用户组在消息内容中。
    replied_user: :class:`bool`
        是否提及正在回复的消息的作者。 默认为 ``True`` 。
    """

    __slots__ = ('everyone', 'users', 'roles', 'replied_user')

    def __init__(
            self,
            *,
            everyone: bool = default,
            users: Union[bool, List[Member]] = default,
            roles: Union[bool, List[Role]] = default,
            replied_user: bool = default,
    ):
        self.everyone = everyone
        self.users = users
        self.roles = roles
        self.replied_user = replied_user

    @classmethod
    def all(cls: Type[A]) -> A:
        """返回一个 :class:`AllowedMentions` 的工厂方法，其中所有字段都显式设置为 ``True``"""
        return cls(everyone=True, users=True, roles=True, replied_user=True)

    @classmethod
    def none(cls: Type[A]) -> A:
        """一个工厂方法，返回一个 :class:`AllowedMentions`，所有字段都设置为 ``False``"""
        return cls(everyone=False, users=False, roles=False, replied_user=False)

    def to_dict(self) -> AllowedMentionsPayload:
        parse = []
        data = {}

        if self.everyone:
            parse.append('everyone')

        if self.users == True:
            parse.append('users')
        elif self.users != False:
            data['users'] = [x.id for x in self.users]

        if self.roles == True:
            parse.append('roles')
        elif self.roles != False:
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
