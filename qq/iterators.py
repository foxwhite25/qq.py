import asyncio
import datetime
from typing import AsyncIterator, TypeVar, Awaitable, Any, Optional, Callable, Union, List

from qq.error import NoMoreItems
from .guild import Guild
from .types.guild import Guild as GuildPayload
from .utils import maybe_coroutine

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

    def create_guild(self, data, channels):
        from .guild import Guild

        return Guild(data=data, channels=channels)

    async def fill_guilds(self):
        if self._get_retrieve():
            data = await self._retrieve_guilds(self.retrieve)
            if self.limit is None or len(data) < 100:
                self.limit = 0

            if self._filter:
                data = filter(self._filter, data)

            for element in data:
                channels = await self.get_guild_channels(element['id'])
                await self.guilds.put(self.create_guild(element, channels=channels))

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
