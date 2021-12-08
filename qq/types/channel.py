from typing import Literal, TypedDict, Optional, Union

ChannelType = Literal[0, 1, 2, 3, 4, 10005, 10006, 10007]


class _BaseChannel(TypedDict):
    id: str
    name: str


class _BaseGuildChannel(_BaseChannel):
    guild_id: str
    position: int
    parent_id: Optional[str]
    owner_id: str


class TextChannel(_BaseGuildChannel):
    type: Literal[0]
    sub_type: str


class LiveChannel(_BaseGuildChannel):
    type: Literal[5]


class VoiceChannel(_BaseGuildChannel):
    type: Literal[2]


class CategoryChannel(_BaseGuildChannel):
    type: Literal[4]


class AppChannel(_BaseGuildChannel):
    type: Literal[6]


class ThreadChannel(_BaseGuildChannel):
    type: Literal[7]


GuildChannel = Union[TextChannel, LiveChannel, VoiceChannel, CategoryChannel, AppChannel, ThreadChannel]
Channel = Union[GuildChannel]
