from typing import Optional, TypedDict
from .user import User


class PartialEmoji(TypedDict):
    id: Optional[int]
    name: Optional[str]


class Emoji(PartialEmoji, total=False):
    pass


class EditEmoji(TypedDict):
    name: str
    roles: Optional[int]
