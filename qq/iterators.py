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

import asyncio
import datetime
from typing import AsyncIterator, TypeVar, Awaitable, Any, Optional, Callable, Union, List, TYPE_CHECKING

from .error import NoMoreItems
from .object import Object
from .utils import maybe_coroutine

if TYPE_CHECKING:
    from .types.guild import (
        Guild as GuildPayload,
    )
    from .types.message import (
        Message as MessagePayload,
    )
    from .member import Member
    from .message import Message
    from .guild import Guild

__all__ = (
    'GuildIterator',
    'MemberIterator',
)

T = TypeVar('T')
OT = TypeVar('OT')
_Func = Callable[[T], Union[OT, Awaitable[OT]]]


class _AsyncIterator(AsyncIterator[T]):
    __slots__ = ()

    async def next(self) -> T:
        raise NotImplementedError

    def get(self, **attrs: Any) -> Awaitable[Optional[T]]:
        def predicate(elem: T):
            for attr, val in attrs.items():
                nested = attr.split('__')
                obj = elem
                for attribute in nested:
                    obj = getattr(obj, attribute)

                if obj != val:
                    return False
            return True

        return self.find(predicate)

    async def find(self, predicate: _Func[T, bool]) -> Optional[T]:
        while True:
            try:
                elem = await self.next()
            except NoMoreItems:
                return None

            ret = await maybe_coroutine(predicate, elem)
            if ret:
                return elem

    def chunk(self, max_size: int):
        if max_size <= 0:
            raise ValueError('async iterator chunk sizes must be greater than 0.')
        return _ChunkedAsyncIterator(self, max_size)

    def map(self, func: _Func[T, OT]):
        return _MappedAsyncIterator(self, func)

    def filter(self, predicate: _Func[T, bool]):
        return _FilteredAsyncIterator(self, predicate)

    async def flatten(self) -> List[T]:
        return [element async for element in self]

    async def __anext__(self) -> T:
        try:
            return await self.next()
        except NoMoreItems:
            raise StopAsyncIteration()


class _ChunkedAsyncIterator(_AsyncIterator[List[T]]):
    def __init__(self, iterator, max_size):
        self.iterator = iterator
        self.max_size = max_size

    async def next(self) -> List[T]:
        ret: List[T] = []
        n = 0
        while n < self.max_size:
            try:
                item = await self.iterator.next()
            except NoMoreItems:
                if ret:
                    return ret
                raise
            else:
                ret.append(item)
                n += 1
        return ret


class _MappedAsyncIterator(_AsyncIterator[T]):
    def __init__(self, iterator, func):
        self.iterator = iterator
        self.func = func

    async def next(self) -> T:
        # this raises NoMoreItems and will propagate appropriately
        item = await self.iterator.next()
        return await maybe_coroutine(self.func, item)


def _identity(x):
    return x


class _FilteredAsyncIterator(_AsyncIterator[T]):
    def __init__(self, iterator, predicate):
        self.iterator = iterator

        if predicate is None:
            predicate = _identity

        self.predicate = predicate

    async def next(self) -> T:
        getter = self.iterator.next
        pred = self.predicate
        while True:
            # propagate NoMoreItems similar to _MappedAsyncIterator
            item = await getter()
            ret = await maybe_coroutine(pred, item)
            if ret:
                return item


class GuildIterator(_AsyncIterator['Guild']):
    def __init__(self, bot, limit, before=None, after=None):

        self.bot = bot
        self.limit = limit
        self.before = before
        self.after = after

        self._filter = None
        self.state = self.bot._connection

        self.get_guilds = self.bot.http.get_guilds
        self.get_guild_channels = self.bot.http.get_guild_channels
        self.guilds = asyncio.Queue()

        if self.before and self.after:
            self._retrieve_guilds = self._retrieve_guilds_before_strategy  # type: ignore
            self._filter = lambda m: int(m['id']) > self.after.id
        elif self.after:
            self._retrieve_guilds = self._retrieve_guilds_after_strategy  # type: ignore
        else:
            self._retrieve_guilds = self._retrieve_guilds_before_strategy  # type: ignore

    async def next(self) -> Guild:
        if self.guilds.empty():
            await self.fill_guilds()

        try:
            return self.guilds.get_nowait()
        except asyncio.QueueEmpty:
            raise NoMoreItems()

    def _get_retrieve(self):
        l = self.limit
        if l is None or l > 100:
            r = 100
        else:
            r = l
        self.retrieve = r
        return r > 0

    def create_guild(self, data):
        from .guild import Guild

        return Guild(data=data, state=self.state)

    async def fill_guilds(self):
        if self._get_retrieve():
            data = await self._retrieve_guilds(self.retrieve)
            if self.limit is None or len(data) < 100:
                self.limit = 0

            if self._filter:
                data = filter(self._filter, data)

            for element in data:
                await self.guilds.put(self.create_guild(element))

    async def _retrieve_guilds(self, retrieve) -> List[Guild]:
        """Retrieve guilds and update next parameters."""
        raise NotImplementedError

    async def _retrieve_guilds_before_strategy(self, retrieve):
        """Retrieve guilds using before parameter."""
        before = self.before.id if self.before else None
        data: List[GuildPayload] = await self.get_guilds(retrieve, before=before)
        if len(data):
            if self.limit is not None:
                self.limit -= retrieve
        return data

    async def _retrieve_guilds_after_strategy(self, retrieve):
        """Retrieve guilds using after parameter."""
        after = self.after.id if self.after else None
        data: List[GuildPayload] = await self.get_guilds(retrieve, after=after)
        if len(data):
            if self.limit is not None:
                self.limit -= retrieve
        return data


class MemberIterator(_AsyncIterator['Member']):
    def __init__(self, guild, limit=1000, after=None):

        if isinstance(after, int):
            after = Object(id=after)

        self.guild = guild
        self.limit = limit
        self.after = after or 0

        self.state = self.guild._state
        self.get_members = self.state.http.get_members
        self.members = asyncio.Queue()

    async def next(self) -> Member:
        if self.members.empty():
            await self.fill_members()

        try:
            return self.members.get_nowait()
        except asyncio.QueueEmpty:
            raise NoMoreItems()

    def _get_retrieve(self):
        l = self.limit
        if l is None or l > 400:
            r = 400
        else:
            r = l
        self.retrieve = r
        return r > 0

    async def fill_members(self):
        if self._get_retrieve():
            after = self.after.id if self.after else None
            data = await self.get_members(self.guild.id, self.retrieve, after)
            if not data:
                # no data, terminate
                return

            self.after = Object(id=int(data[-1]['user']['id']))

            for element in reversed(data):
                await self.members.put(self.create_member(element))

    def create_member(self, data):
        from .member import Member

        return Member(data=data, guild=self.guild, state=self.state)


class HistoryIterator(_AsyncIterator['Message']):
    """用于接收频道消息历史的迭代器。
    消息端点有两个我们关心的行为：
    如果指定了 ``before`` ，则消息端点返回 ``before`` 之前的 ``limit`` 最新消息，以最新的优先排序。
    要填充超过 100 条消息，请将 ``before`` 参数更新为收到的最旧消息。消息将按时间顺序返回。
    如果指定了 ``after``，它返回 ``after`` 之后的 ``limit`` 最旧的消息，以最新的在前排序。
    要填充超过 100 条消息，请将 ``after`` 参数更新为收到的最新消息。如果消息没有反转，它们将乱序（99-0、199-100 等）
    注意如果同时指定了 ``before`` 和 ``after`` ，则 ``before`` 将被忽略。

    Parameters
    -----------
    messageable: :class:`abc.Messageable`
        可从中检索消息历史记录的 Messageable 类。

    limit: :class:`int`
        要检索的最大消息数

    before: Optional[:class:`datetime.datetime`]
        所有消息必须在其之前的消息。

    after: Optional[:class:`datetime.datetime`]
        所有消息必须在其后的消息。

    around: Optional[:class:`datetime.datetime`]
        所有消息必须围绕的消息。 Limit max 101。注意，如果limit是偶数，这将最多返回limit+1条消息。

    oldest_first: Optional[:class:`bool`]
        如果设置为 ``True``，以最旧->最新的顺序返回消息。如果指定了“after”，则默认为“True”，否则为“False”。
    """

    def __init__(self, messageable, limit, before=None, after=None, around=None, oldest_first=None):

        if oldest_first is None:
            self.reverse = after is not None
        else:
            self.reverse = oldest_first

        self.messageable = messageable
        self.limit = limit
        self.before = before
        self.after = after or 0
        self.around = around

        self._filter = None  # message dict -> bool

        self.state = self.messageable._state
        self.logs_from = self.state.http.logs_from
        self.messages = asyncio.Queue()

        if self.around:
            if self.limit is None:
                raise ValueError('历史不支持limit=None')
            if self.limit > 101:
                raise ValueError("指定 around 参数时的历史最大限制 101")
            elif self.limit == 101:
                self.limit = 100  # Thanks qq

            self._retrieve_messages = self._retrieve_messages_around_strategy  # type: ignore
            if self.before and self.after:
                self._filter = lambda m: \
                    self.timestamp(self.after) < self.timestamp(m['timestamp']) < self.timestamp(
                        self.before)  # type: ignore
            elif self.before:
                self._filter = lambda m: self.timestamp(m['timestamp']) < self.timestamp(self.before)  # type: ignore
            elif self.after:
                self._filter = lambda m: self.timestamp(self.after) < self.timestamp(m['timestamp'])  # type: ignore
        else:
            if self.reverse:
                self._retrieve_messages = self._retrieve_messages_after_strategy  # type: ignore
                if self.before:
                    self._filter = lambda m: self.timestamp(m['timestamp']) < self.timestamp(
                        self.before)  # type: ignore
            else:
                self._retrieve_messages = self._retrieve_messages_before_strategy  # type: ignore
                if self.after and self.after != 0:
                    self._filter = lambda m: self.timestamp(m['timestamp']) > self.timestamp(self.after)  # type: ignore

    def timestamp(self, dt: Union[datetime.datetime, str]):
        if isinstance(dt, str):
            dt = datetime.datetime.strptime(dt, "%Y-%m-%dT%H:%M:%SZ")
        return int(datetime.datetime.timestamp(dt))

    async def next(self) -> Message:
        if self.messages.empty():
            await self.fill_messages()

        try:
            return self.messages.get_nowait()
        except asyncio.QueueEmpty:
            raise NoMoreItems()

    def _get_retrieve(self):
        l = self.limit
        if l is None or l > 100:
            r = 100
        else:
            r = l
        self.retrieve = r
        return r > 0

    async def fill_messages(self):
        if not hasattr(self, 'channel'):
            # do the required set up
            channel = await self.messageable._get_channel()
            self.channel = channel

        if self._get_retrieve():
            data = await self._retrieve_messages(self.retrieve)
            if len(data) < 100:
                self.limit = 0  # terminate the infinite loop

            if self.reverse:
                data = reversed(data)
            if self._filter:
                data = filter(self._filter, data)

            channel = self.channel
            for element in data:
                await self.messages.put(self.state.create_message(channel=channel, data=element))

    async def _retrieve_messages(self, retrieve) -> List[Message]:
        """检索消息并更新下一个参数"""
        raise NotImplementedError

    async def _retrieve_messages_before_strategy(self, retrieve):
        """使用 before 参数检索消息。"""
        before = self.timestamp(self.before) if self.before else None
        data: List[MessagePayload] = await self.logs_from(self.channel.id, retrieve, before=before)
        if len(data):
            if self.limit is not None:
                self.limit -= retrieve
            self.before = datetime.datetime.strptime(data[-1]['timestamp'], "%Y-%m-%dT%H:%M:%SZ")
        return data

    async def _retrieve_messages_after_strategy(self, retrieve):
        """使用 after 参数检索消息。"""
        after = self.timestamp(self.after) if self.after else None
        data: List[MessagePayload] = await self.logs_from(self.channel.id, retrieve, after=after)
        if len(data):
            if self.limit is not None:
                self.limit -= retrieve
            self.after = datetime.datetime.strptime(data[0]['timestamp'], "%Y-%m-%dT%H:%M:%SZ")
        return data

    async def _retrieve_messages_around_strategy(self, retrieve):
        """使用 around 参数检索消息。"""
        if self.around:
            around = self.around.id if self.around else None
            data: List[MessagePayload] = await self.logs_from(self.channel.id, retrieve, around=around)
            self.around = None
            return data
        return []
