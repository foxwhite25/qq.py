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

import random
import time
from typing import Callable, Generic, Literal, TypeVar, overload, Union

T = TypeVar('T', bool, Literal[True], Literal[False])

__all__ = (
    'ExponentialBackoff',
)


class ExponentialBackoff(Generic[T]):
    def __init__(self, base: int = 1, *, integral: T = False):
        self._base: int = base

        self._exp: int = 0
        self._max: int = 10
        self._reset_time: int = base * 2 ** 11
        self._last_invocation: float = time.monotonic()

        # Use our own random instance to avoid messing with global one
        rand = random.Random()
        rand.seed()

        self._randfunc: Callable[..., Union[int, float]] = rand.randrange if integral else rand.uniform  # type: ignore

    @overload
    def delay(self: ExponentialBackoff[Literal[False]]) -> float:
        ...

    @overload
    def delay(self: ExponentialBackoff[Literal[True]]) -> int:
        ...

    @overload
    def delay(self: ExponentialBackoff[bool]) -> Union[int, float]:
        ...

    def delay(self) -> Union[int, float]:
        """计算下一个延迟
        根据指数退避算法返回要等待的下一个延迟。
        这是一个介于 0 和 基数 * 2^exp 之间的值，其中 exp 从 1 开始，并在每次调用此方法时递增，最大为 10。
        如果自上次重试以来已经过去了超过基数 * 2^11 的时间段，则指数将重置为 1。
        """
        invocation = time.monotonic()
        interval = invocation - self._last_invocation
        self._last_invocation = invocation

        if interval > self._reset_time:
            self._exp = 0

        self._exp = min(self._exp + 1, self._max)
        return self._randfunc(0, self._base * 2 ** self._exp)
