from typing import Optional, List, TypedDict

from qq.types.channel import GuildChannel
from qq.types.member import Member
from qq.types.role import Role


class _UnavailableGuildOptional(TypedDict, total=False):
    unavailable: bool


class UnavailableGuild(_UnavailableGuildOptional):
    id: str


class _GuildOptional(TypedDict, total=False):
    owner: bool
    joined_at: Optional[str]
    large: bool
    member_count: int
    members: List[Member]
    channels: List[GuildChannel]
    max_members: int


class _BaseGuildPreview(UnavailableGuild):
    name: str
    icon: Optional[str]
    description: Optional[str]


class Guild(_BaseGuildPreview, _GuildOptional):
    owner_id: str
    afk_timeout: int
    roles: List[Role]
