from typing import Literal, Optional, TypedDict


class PartialUser(TypedDict):
    id: str
    username: str
    avatar: Optional[str]


class User(PartialUser, total=False):
    bot: bool
