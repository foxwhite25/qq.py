from typing import TypedDict

from .user import User
from ..utils import SnowflakeList


class Nickname(TypedDict):
    nick: str


class PartialMember(TypedDict):
    roles: SnowflakeList
    joined_at: str


class Member(PartialMember, total=False):
    guild_id: str
    user: User
    nick: str


class _OptionalMemberWithUser(PartialMember, total=False):
    avatar: str
    nick: str


class MemberWithUser(_OptionalMemberWithUser):
    user: User


class UserWithMember(User, total=False):
    member: _OptionalMemberWithUser
