from typing import TypedDict

from .role import Role
from .user import User


class Nickname(TypedDict):
    nick: str


class PartialMember(TypedDict):
    roles: list[Role]
    joined_at: str


class Member(PartialMember, total=False):
    guild_id: str
    user: User
    nick: str
