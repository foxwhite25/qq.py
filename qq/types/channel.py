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

from typing import Literal, TypedDict, Optional, Union

from .user import PartialUser

ChannelType = Literal[0, 1, 2, 3, 4, 10005, 10006, 10007]


class _BaseChannel(TypedDict):
    id: str
    name: str


class _BaseGuildChannel(_BaseChannel):
    guild_id: str
    position: int
    parent_id: Optional[str]
    owner_id: str
    private_type: int


class DMChannel(_BaseChannel):
    channel_id: str
    type: Literal[1]
    guild_id: str
    create_time: str
    last_message_id: Optional[str]
    recipients: PartialUser


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
Channel = Union[GuildChannel, DMChannel]
