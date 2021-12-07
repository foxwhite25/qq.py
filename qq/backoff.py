from __future__ import annotations

import time
import random
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
        """Compute the next delay
        Returns the next delay to wait according to the exponential
        backoff algorithm.  This is a value between 0 and base * 2^exp
        where exponent starts off at 1 and is incremented at every
        invocation of this method up to a maximum of 10.
        If a period of more than base * 2^11 has passed since the last
        retry, the exponent is reset to 1.
        """
        invocation = time.monotonic()
        interval = invocation - self._last_invocation
        self._last_invocation = invocation

        if interval > self._reset_time:
            self._exp = 0

        self._exp = min(self._exp + 1, self._max)
        return self._randfunc(0, self._base * 2 ** self._exp)
