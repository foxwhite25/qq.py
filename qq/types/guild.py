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


class ChannelPositionUpdate(TypedDict):
    id: int
    position: Optional[int]
    parent_id: Optional[int]
