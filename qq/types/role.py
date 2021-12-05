from __future__ import annotations

from typing import TypedDict


class Role(TypedDict):
    id: str
    name: str
    color: int
    hoist: bool
    number: int
    member_limit: int
