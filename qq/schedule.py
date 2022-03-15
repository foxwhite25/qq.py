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

import datetime
from typing import TYPE_CHECKING, Optional

from .member import Member
from .types.schedule import Schedule as SchedulePayload

__all__ = ('Schedule',)

if TYPE_CHECKING:
    from .abc import GuildChannel
    from .state import ConnectionState
    from .guild import Guild


class Schedule:
    """代表一个 :class:`AppChannel` 的日历。。

    Attributes
    ----------
    id: :class:`str`
        一个 datetime 对象，它指定成员加入频道的日期和时间。
        如果成员离开并重新加入频道，这将是最新的日期。在某些情况下，这可以是 ``None`` 。
    name: :class:`str`
        成员所属的频道。
    guild: :class:`Guild`
        日程所在的频道
    channel: :class:`GuildChannel`
        日程所在的频道
    description: Optional[:class:`str`]
        用户的频道特定昵称。
    start: :class:`datatime.datetime`
        日程开始的时间。
    end: start: :class:`datatime.datetime`
        日程结束的时间。
    creator: :class:`Member`
        日程创建者。
    jump_channel: :class:`GuildChannel`
        日程跳转频道。
    remind_type: :class:`str`
        日程提醒类型。

        +-----------+--------------+
        | 提醒类型 id	  | 描述           |
        +===========+==============+
        | 0         | 不提醒          |
        | 1         | 开始时提醒        |
        | 2         | 开始前 5 分钟提醒   |
        | 3         | 开始前 15 分钟提醒  |
        | 4         | 开始前 30 分钟提醒  |
        | 5         | 开始前 60 分钟提醒  |
        +-----------+--------------+

    """

    __slots__ = (
        '_state',
        'id',
        'name',
        'description',
        'start',
        'end',
        'creator',
        'jump_channel',
        'remind_type',
        'channel',
        'guild'
    )

    if TYPE_CHECKING:
        name: str
        id: int
        description: Optional[str]

    def __init__(self, data: SchedulePayload, state: ConnectionState, guild: Guild, channel: GuildChannel):
        self.id = int(data['id'])
        self.name = data['name']
        self.description = data.get('description', None)
        self.start = datetime.datetime.fromtimestamp(int(data['start_timestamp']) / 1000)
        self.end = datetime.datetime.fromtimestamp(int(data['end_timestamp']) / 1000)
        self.creator = Member(data=data['creator'], guild=guild, state=state)
        self.jump_channel = guild.get_channel(int(data['jump_channel_id']))
        self.remind_type = data['remind_type']
        self._state = state
        self.channel = channel
        self.guild = guild

    @classmethod
    def from_id(cls, channel: GuildChannel, schedule_id: int):
        """
        创建一个不完全的 :class:`Schedule` ，主要用语 :meth:`Schedule.delete`
        """
        self = cls.__new__(cls)
        self.channel = channel
        self.id = schedule_id
        return self

    async def delete(self, reason: Optional[str] = None):
        """|coro|
        删除这个日历。
        """
        await self._state.http.remove_schedule(self.channel.id, self.id, reason=reason)
