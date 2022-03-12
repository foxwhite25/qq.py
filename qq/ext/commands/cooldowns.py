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
import time
from collections import deque
from typing import Any, Callable, Deque, Dict, Optional, Type, TypeVar, TYPE_CHECKING

from qq.enum import Enum
from .errors import MaxConcurrencyReached

if TYPE_CHECKING:
    from ...message import Message

__all__ = (
    'BucketType',
    'Cooldown',
    'CooldownMapping',
    'DynamicCooldownMapping',
    'MaxConcurrency',
)

C = TypeVar('C', bound='CooldownMapping')
MC = TypeVar('MC', bound='MaxConcurrency')


class BucketType(Enum):
    default = 0
    user = 1
    guild = 2
    channel = 3
    member = 4
    category = 5
    role = 6

    def get_key(self, msg: Message) -> Any:
        if self is BucketType.user:
            return msg.author.id
        elif self is BucketType.guild:
            return (msg.guild or msg.author).id
        elif self is BucketType.channel:
            return msg.channel.id
        elif self is BucketType.member:
            return ((msg.guild and msg.guild.id), msg.author.id)
        elif self is BucketType.category:
            return (msg.channel.category or msg.channel).id  # type: ignore
        elif self is BucketType.role:
            # we return the channel id of a private-channel as there are only roles in guilds
            # and that yields the same result as for a guild with only the @everyone role
            # NOTE: PrivateChannel doesn't actually have an id attribute but we assume we are
            # recieving a DMChannel or GroupChannel which inherit from PrivateChannel and do
            return (msg.channel if isinstance(msg.channel, PrivateChannel) else msg.author.top_role).id  # type: ignore

    def __call__(self, msg: Message) -> Any:
        return self.get_key(msg)


class Cooldown:
    """表示命令的冷却时间。

    Attributes
    -----------
    rate: :class:`int`
        每 :attr:`per` 秒可用的令牌总数。
    per: :class:`float`
        以秒为单位的冷却时间长度。
    """

    __slots__ = ('rate', 'per', '_window', '_tokens', '_last')

    def __init__(self, rate: float, per: float) -> None:
        self.rate: int = int(rate)
        self.per: float = float(per)
        self._window: float = 0.0
        self._tokens: int = self.rate
        self._last: float = 0.0

    def get_tokens(self, current: Optional[float] = None) -> int:
        """返回应用速率限制之前可用令牌的数量。

        Parameters
        ------------
        current: Optional[:class:`float`]
            自 Unix 纪元以来计算令牌的时间（以秒为单位）。如果未提供，则使用 :func:`time.time()`。

        Returns
        --------
        :class:`int`
            应用冷却前可用的令牌数量。
        """
        if not current:
            current = time.time()

        tokens = self._tokens

        if current > self._window + self.per:
            tokens = self.rate
        return tokens

    def get_retry_after(self, current: Optional[float] = None) -> float:
        """返回冷却时间重置之前的时间（以秒为单位）。

        Parameters
        -------------
        current: Optional[:class:`float`]
            自 Unix 纪元以来的当前时间（以秒为单位）。
            如果未提供，则使用 :func:`time.time()` 。

        Returns
        -------
        :class:`float`
            在此冷却时间将被重置之前等待的秒数。
        """
        current = current or time.time()
        tokens = self.get_tokens(current)

        if tokens == 0:
            return self.per - (current - self._window)

        return 0.0

    def update_rate_limit(self, current: Optional[float] = None) -> Optional[float]:
        """更新冷却速度限制。

        Parameters
        -------------
        current: Optional[:class:`float`]
            自 Unix 纪元以来更新速率限制的时间（以秒为单位）。
            如果未提供，则使用 :func:`time.time()` 。

        Returns
        -------
        Optional[:class:`float`]
            如果速率受限，则以秒为单位的重试时间。
        """
        current = current or time.time()
        self._last = current

        self._tokens = self.get_tokens(current)

        # first token used means that we start a new rate limit window
        if self._tokens == self.rate:
            self._window = current

        # check if we are rate limited
        if self._tokens == 0:
            return self.per - (current - self._window)

        # we're not so decrement our tokens
        self._tokens -= 1

    def reset(self) -> None:
        """将冷却重置为其初始状态。"""
        self._tokens = self.rate
        self._last = 0.0

    def copy(self) -> Cooldown:
        """创建此冷却时间的副本。

        Returns
        --------
        :class:`Cooldown`
            此冷却时间的新实例。
        """
        return Cooldown(self.rate, self.per)

    def __repr__(self) -> str:
        return f'<Cooldown rate: {self.rate} per: {self.per} window: {self._window} tokens: {self._tokens}>'


class CooldownMapping:
    def __init__(
            self,
            original: Optional[Cooldown],
            type: Callable[[Message], Any],
    ) -> None:
        if not callable(type):
            raise TypeError('冷却时间类型必须是 BucketType 或可调用')

        self._cache: Dict[Any, Cooldown] = {}
        self._cooldown: Optional[Cooldown] = original
        self._type: Callable[[Message], Any] = type

    def copy(self) -> CooldownMapping:
        ret = CooldownMapping(self._cooldown, self._type)
        ret._cache = self._cache.copy()
        return ret

    @property
    def valid(self) -> bool:
        return self._cooldown is not None

    @property
    def type(self) -> Callable[[Message], Any]:
        return self._type

    @classmethod
    def from_cooldown(cls: Type[C], rate, per, type) -> C:
        return cls(Cooldown(rate, per), type)

    def _bucket_key(self, msg: Message) -> Any:
        return self._type(msg)

    def _verify_cache_integrity(self, current: Optional[float] = None) -> None:
        # we want to delete all cache objects that haven't been used
        # in a cooldown window. e.g. if we have a  command that has a
        # cooldown of 60s and it has not been used in 60s then that key should be deleted
        current = current or time.time()
        dead_keys = [k for k, v in self._cache.items() if current > v._last + v.per]
        for k in dead_keys:
            del self._cache[k]

    def create_bucket(self, message: Message) -> Cooldown:
        return self._cooldown.copy()  # type: ignore

    def get_bucket(self, message: Message, current: Optional[float] = None) -> Cooldown:
        if self._type is BucketType.default:
            return self._cooldown  # type: ignore

        self._verify_cache_integrity(current)
        key = self._bucket_key(message)
        if key not in self._cache:
            bucket = self.create_bucket(message)
            if bucket is not None:
                self._cache[key] = bucket
        else:
            bucket = self._cache[key]

        return bucket

    def update_rate_limit(self, message: Message, current: Optional[float] = None) -> Optional[float]:
        bucket = self.get_bucket(message, current)
        return bucket.update_rate_limit(current)


class DynamicCooldownMapping(CooldownMapping):

    def __init__(
            self,
            factory: Callable[[Message], Cooldown],
            type: Callable[[Message], Any]
    ) -> None:
        super().__init__(None, type)
        self._factory: Callable[[Message], Cooldown] = factory

    def copy(self) -> DynamicCooldownMapping:
        ret = DynamicCooldownMapping(self._factory, self._type)
        ret._cache = self._cache.copy()
        return ret

    @property
    def valid(self) -> bool:
        return True

    def create_bucket(self, message: Message) -> Cooldown:
        return self._factory(message)


class _Semaphore:
    """这个类是信号量的一个版本。

    如果你想知道为什么没有使用 asyncio.Semaphore，那是因为它没有公开内部值。
    这个内部值是必要的，因为我需要同时支持 `wait=True` 和 `wait=False`。

    也可以使用 asyncio.Queue 来做到这一点——但它并不是那么低效，
    因为在内部使用两个队列并且对于基本上是一个计数器的东西来说有点矫枉过正。
    """

    __slots__ = ('value', 'loop', '_waiters')

    def __init__(self, number: int) -> None:
        self.value: int = number
        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
        self._waiters: Deque[asyncio.Future] = deque()

    def __repr__(self) -> str:
        return f'<_Semaphore value={self.value} waiters={len(self._waiters)}>'

    def locked(self) -> bool:
        return self.value == 0

    def is_active(self) -> bool:
        return len(self._waiters) > 0

    def wake_up(self) -> None:
        while self._waiters:
            future = self._waiters.popleft()
            if not future.done():
                future.set_result(None)
                return

    async def acquire(self, *, wait: bool = False) -> bool:
        if not wait and self.value <= 0:
            # signal that we're not acquiring
            return False

        while self.value <= 0:
            future = self.loop.create_future()
            self._waiters.append(future)
            try:
                await future
            except:
                future.cancel()
                if self.value > 0 and not future.cancelled():
                    self.wake_up()
                raise

        self.value -= 1
        return True

    def release(self) -> None:
        self.value += 1
        self.wake_up()


class MaxConcurrency:
    __slots__ = ('number', 'per', 'wait', '_mapping')

    def __init__(self, number: int, *, per: BucketType, wait: bool) -> None:
        self._mapping: Dict[Any, _Semaphore] = {}
        self.per: BucketType = per
        self.number: int = number
        self.wait: bool = wait

        if number <= 0:
            raise ValueError('max_concurrency \'number\' cannot be less than 1')

        if not isinstance(per, BucketType):
            raise TypeError(f'max_concurrency \'per\' must be of type BucketType not {type(per)!r}')

    def copy(self: MC) -> MC:
        return self.__class__(self.number, per=self.per, wait=self.wait)

    def __repr__(self) -> str:
        return f'<MaxConcurrency per={self.per!r} number={self.number} wait={self.wait}>'

    def get_key(self, message: Message) -> Any:
        return self.per.get_key(message)

    async def acquire(self, message: Message) -> None:
        key = self.get_key(message)

        try:
            sem = self._mapping[key]
        except KeyError:
            self._mapping[key] = sem = _Semaphore(self.number)

        acquired = await sem.acquire(wait=self.wait)
        if not acquired:
            raise MaxConcurrencyReached(self.number, self.per)

    async def release(self, message: Message) -> None:
        # Technically there's no reason for this function to be async
        # But it might be more useful in the future
        key = self.get_key(message)

        try:
            sem = self._mapping[key]
        except KeyError:
            # ...? peculiar
            return
        else:
            sem.release()

        if sem.value >= self.number and not sem.is_active():
            del self._mapping[key]
