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
import inspect
import sys
import traceback
from collections.abc import Sequence
from typing import (
    Any,
    Awaitable,
    Callable,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)

import aiohttp

import qq
from qq.backoff import ExponentialBackoff
from qq.utils import MISSING

# fmt: off
__all__ = (
    'loop',
)
# fmt: on

T = TypeVar('T')
_func = Callable[..., Awaitable[Any]]
LF = TypeVar('LF', bound=_func)
FT = TypeVar('FT', bound=_func)
ET = TypeVar('ET', bound=Callable[[Any, BaseException], Awaitable[Any]])


class SleepHandle:
    __slots__ = ('future', 'loop', 'handle')

    def __init__(self, dt: datetime.datetime, *, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop
        self.future = future = loop.create_future()
        relative_delta = qq.utils.compute_timedelta(dt)
        self.handle = loop.call_later(relative_delta, future.set_result, True)

    def recalculate(self, dt: datetime.datetime) -> None:
        self.handle.cancel()
        relative_delta = qq.utils.compute_timedelta(dt)
        self.handle = self.loop.call_later(relative_delta, self.future.set_result, True)

    def wait(self) -> asyncio.Future[Any]:
        return self.future

    def done(self) -> bool:
        return self.future.done()

    def cancel(self) -> None:
        self.handle.cancel()
        self.future.cancel()


class Loop(Generic[LF]):
    """抽象循环和重新连接逻辑的后台任务助手。创建它的主要方法是通过 :func:`loop` 。
    """

    def __init__(
            self,
            coro: LF,
            seconds: float,
            hours: float,
            minutes: float,
            time: Union[datetime.time, Sequence[datetime.time]],
            count: Optional[int],
            reconnect: bool,
            loop: asyncio.AbstractEventLoop,
    ) -> None:
        self.coro: LF = coro
        self.reconnect: bool = reconnect
        self.loop: asyncio.AbstractEventLoop = loop
        self.count: Optional[int] = count
        self._current_loop = 0
        self._handle: Optional[SleepHandle] = None
        self._task: Optional[asyncio.Task[None]] = None
        self._injected = None
        self._valid_exception = (
            OSError,
            qq.GatewayNotFound,
            qq.ConnectionClosed,
            aiohttp.ClientError,
            asyncio.TimeoutError,
        )

        self._before_loop = None
        self._after_loop = None
        self._is_being_cancelled = False
        self._has_failed = False
        self._stop_next_iteration = False

        if self.count is not None and self.count <= 0:
            raise ValueError('计数必须大于 0 或无。')

        self.change_interval(seconds=seconds, minutes=minutes, hours=hours, time=time)
        self._last_iteration_failed = False
        self._last_iteration: datetime.datetime = MISSING
        self._next_iteration = None

        if not inspect.iscoroutinefunction(self.coro):
            raise TypeError(f'预期协程函数，而不是 {type(self.coro).__name__!r}。')

    async def _call_loop_function(self, name: str, *args: Any, **kwargs: Any) -> None:
        coro = getattr(self, '_' + name)
        if coro is None:
            return

        if self._injected is not None:
            await coro(self._injected, *args, **kwargs)
        else:
            await coro(*args, **kwargs)

    def _try_sleep_until(self, dt: datetime.datetime):
        self._handle = SleepHandle(dt=dt, loop=self.loop)
        return self._handle.wait()

    async def _loop(self, *args: Any, **kwargs: Any) -> None:
        backoff = ExponentialBackoff()
        await self._call_loop_function('before_loop')
        self._last_iteration_failed = False
        if self._time is not MISSING:
            # the time index should be prepared every time the internal loop is started
            self._prepare_time_index()
            self._next_iteration = self._get_next_sleep_time()
        else:
            self._next_iteration = datetime.datetime.now(datetime.timezone.utc)
            await asyncio.sleep(0)  # allows canceling in before_loop
        try:
            if self._stop_next_iteration:  # allow calling stop() before first iteration
                return
            while True:
                # sleep before the body of the task for explicit time intervals
                if self._time is not MISSING:
                    await self._try_sleep_until(self._next_iteration)
                if not self._last_iteration_failed:
                    self._last_iteration = self._next_iteration
                    self._next_iteration = self._get_next_sleep_time()
                try:
                    await self.coro(*args, **kwargs)
                    self._last_iteration_failed = False
                except self._valid_exception:
                    self._last_iteration_failed = True
                    if not self.reconnect:
                        raise
                    await asyncio.sleep(backoff.delay())
                else:
                    if self._stop_next_iteration:
                        return

                    # sleep after the body of the task for relative time intervals
                    if self._time is MISSING:
                        await self._try_sleep_until(self._next_iteration)

                    self._current_loop += 1
                    if self._current_loop == self.count:
                        break

        except asyncio.CancelledError:
            self._is_being_cancelled = True
            raise
        except Exception as exc:
            self._has_failed = True
            await self._call_loop_function('error', exc)
            raise exc
        finally:
            await self._call_loop_function('after_loop')
            if self._handle:
                self._handle.cancel()
            self._is_being_cancelled = False
            self._current_loop = 0
            self._stop_next_iteration = False
            self._has_failed = False

    def __get__(self, obj: T, objtype: Type[T]) -> Loop[LF]:
        if obj is None:
            return self

        copy: Loop[LF] = Loop(
            self.coro,
            seconds=self._seconds,
            hours=self._hours,
            minutes=self._minutes,
            time=self._time,
            count=self.count,
            reconnect=self.reconnect,
            loop=self.loop,
        )
        copy._injected = obj
        copy._before_loop = self._before_loop
        copy._after_loop = self._after_loop
        copy._error = self._error
        setattr(obj, self.coro.__name__, copy)
        return copy

    @property
    def seconds(self) -> Optional[float]:
        """Optional[:class:`float`]: 每次迭代之间的秒数的只读值。如果传递了明确的 ``time`` 值，则为 ``None`` 。
        """
        if self._seconds is not MISSING:
            return self._seconds

    @property
    def minutes(self) -> Optional[float]:
        """Optional[:class:`float`]: 每次迭代之间的分钟数的只读值。如果传递了明确的 ``time`` 值，则为 ``None`` 。
        """
        if self._minutes is not MISSING:
            return self._minutes

    @property
    def hours(self) -> Optional[float]:
        """Optional[:class:`float`]: 每次迭代之间的小时数的只读值。如果传递了明确的 ``time`` 值，则为 ``None`` 。
        """
        if self._hours is not MISSING:
            return self._hours

    @property
    def time(self) -> Optional[List[datetime.time]]:
        """Optional[List[:class:`datetime.time`]]: 此循环运行的确切时间的只读列表。如果通过了相对时间，则为 ``None`` 。
        """
        if self._time is not MISSING:
            return self._time.copy()

    @property
    def current_loop(self) -> int:
        """:class:`int`: 循环的当前迭代。"""
        return self._current_loop

    @property
    def next_iteration(self) -> Optional[datetime.datetime]:
        """Optional[:class:`datetime.datetime`]: 当循环的下一次迭代将发生时。
        """
        if self._task is MISSING:
            return None
        elif self._task and self._task.done() or self._stop_next_iteration:
            return None
        return self._next_iteration

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        r"""|coro|
        调用任务持有的内部回调。
        .. versionadded:: 1.1.0

        Parameters
        ------------
        \*args
            要使用的参数。
        \*\*kwargs
            要使用的关键字参数。
        """

        if self._injected is not None:
            args = (self._injected, *args)

        return await self.coro(*args, **kwargs)

    def start(self, *args: Any, **kwargs: Any) -> asyncio.Task[None]:
        r"""在事件循环中启动内部任务。

        Parameters
        ------------
        \*args
            要使用的参数。
        \*\*kwargs
            要使用的关键字参数。

        Raises
        --------
        RuntimeError
            任务已启动并正在运行。

        Returns
        ---------
        :class:`asyncio.Task`
            已创建的任务。
        """

        if self._task and not self._task.done():
            raise RuntimeError('任务已启动且未完成。')

        if self._injected is not None:
            args = (self._injected, *args)

        if self.loop is MISSING:
            self.loop = asyncio.get_event_loop()

        self._task = self.loop.create_task(self._loop(*args, **kwargs))
        return self._task

    def stop(self) -> None:
        r"""优雅地停止任务运行。与 :meth:`cancel`\ 不同，这允许任务在正常退出之前完成其当前迭代。

        .. note::

            如果内部函数引发了一个可以在完成之前处理的错误，那么它将重试直到成功。
            如果这是不可取的，要么在通过 :meth:`clear_exception_types` 停止之前删除错误处理，要么使用 :meth:`cancel 代替。
        """
        if self._task and not self._task.done():
            self._stop_next_iteration = True

    def _can_be_cancelled(self) -> bool:
        return bool(not self._is_being_cancelled and self._task and not self._task.done())

    def cancel(self) -> None:
        """取消内部任务，如果它正在运行。"""
        if self._can_be_cancelled() and self._task:
            self._task.cancel()

    def restart(self, *args: Any, **kwargs: Any) -> None:
        r"""一种重新启动内部任务的便捷方法。

        .. note::

            由于这个函数的工作方式，任务不会像 :meth:`start` 那样返回。

        Parameters
        ------------
        \*args
            要使用的参数。
        \*\*kwargs
            要使用的关键字参数。
        """

        def restart_when_over(fut: Any, *, args: Any = args, kwargs: Any = kwargs) -> None:
            self._task.remove_done_callback(restart_when_over)
            self.start(*args, **kwargs)

        if self._can_be_cancelled():
            self._task.add_done_callback(restart_when_over)
            self._task.cancel()

    def add_exception_type(self, *exceptions: Type[BaseException]) -> None:
        r"""添加要在重新连接逻辑期间处理的异常类型。
        默认情况下，处理的异常类型是由 :meth:`qq.Client.connect` 处理的异常类型，其中包括很多断网错误。
        如果你正在与引发自己的一组异常的第 3 方库进行交互，则此函数很有用。

        Parameters
        ------------
        \*exceptions: Type[:class:`BaseException`]
            要处理的异常类的参数列表。

        Raises
        --------
        TypeError
            传递的异常要么不是类，要么不是从 BaseException 继承的。
        """

        for exc in exceptions:
            if not inspect.isclass(exc):
                raise TypeError(f'{exc!r} 必须是一个类。')
            if not issubclass(exc, BaseException):
                raise TypeError(f'{exc!r} 必须从 BaseException 继承。')

        self._valid_exception = (*self._valid_exception, *exceptions)

    def clear_exception_types(self) -> None:
        """删除所有处理的异常类型。

        .. note::
            这个操作显然是无法撤消的！

        """
        self._valid_exception = tuple()

    def remove_exception_type(self, *exceptions: Type[BaseException]) -> bool:
        r"""删除在重新连接逻辑期间处理的异常类型。

        Parameters
        ------------
        \*exceptions: Type[:class:`BaseException`]
            要处理的异常类的参数列表。

        Returns
        ---------
        :class:`bool`
            是否已成功删除所有异常。
        """
        old_length = len(self._valid_exception)
        self._valid_exception = tuple(x for x in self._valid_exception if x not in exceptions)
        return len(self._valid_exception) == old_length - len(exceptions)

    def get_task(self) -> Optional[asyncio.Task[None]]:
        """Optional[:class:`asyncio.Task`]: 如果没有运行，则获取内部任务或 ``None`` 。"""
        return self._task if self._task is not MISSING else None

    def is_being_cancelled(self) -> bool:
        """任务是否被取消。"""
        return self._is_being_cancelled

    def failed(self) -> bool:
        """:class:`bool`: 内部任务是否失败。
        """
        return self._has_failed

    def is_running(self) -> bool:
        """:class:`bool`: 检查任务当前是否正在运行。
        """
        return not bool(self._task.done()) if self._task else False

    async def _error(self, *args: Any) -> None:
        exception: Exception = args[-1]
        print(f'内部后台任务 {self.coro.__name__!r} 中未处理的异常。', file=sys.stderr)
        traceback.print_exception(type(exception), exception, exception.__traceback__, file=sys.stderr)

    def before_loop(self, coro: FT) -> FT:
        """在循环开始运行之前注册要调用的协程的装饰器。如果你想在循环开始之前等待一些机器人状态，这很有用，例如 :meth:`qq.Client.wait_until_ready`。

        协程必须不带任何参数（类上下文中的 ``self`` 除外）。

        Parameters
        ------------
        coro: :ref:`coroutine <coroutine>`
            在循环运行之前注册的协程。

        Raises
        -------
        TypeError
            该函数不是协程。
        """

        if not inspect.iscoroutinefunction(coro):
            raise TypeError(f'预期协程函数，收到 {coro.__class__.__name__!r}。')

        self._before_loop = coro
        return coro

    def after_loop(self, coro: FT) -> FT:
        """一个装饰器，注册一个在循环完成运行后要调用的协程。协程必须不带任何参数（类上下文中的 ``self`` 除外）。

        .. note::
            即使在取消期间也会调用此协程。如果需要区分某事是否被取消，请检查 :meth:`is_being_cancelled` 是否为 ``True`` 。

        Parameters
        ------------
        coro: :ref:`coroutine <coroutine>`
            循环完成后要注册的协程。

        Raises
        -------
        TypeError
            该函数不是协程。
        """

        if not inspect.iscoroutinefunction(coro):
            raise TypeError(f'预期协程函数，收到 {coro.__class__.__name__!r}。')

        self._after_loop = coro
        return coro

    def error(self, coro: ET) -> ET:
        """A decorator that registers a coroutine to be called if the task encounters an unhandled exception.
        The coroutine must take only one argument the exception raised (except ``self`` in a class context).
        By default this prints to :data:`sys.stderr` however it could be
        overridden to have a different implementation.
        .. versionadded:: 1.4
        Parameters
        ------------
        coro: :ref:`coroutine <coroutine>`
            The coroutine to register in the event of an unhandled exception.
        Raises
        -------
        TypeError
            The function was not a coroutine.
        """
        if not inspect.iscoroutinefunction(coro):
            raise TypeError(f'预期协程函数，收到 {coro.__class__.__name__!r}。')

        self._error = coro  # type: ignore
        return coro

    def _get_next_sleep_time(self) -> datetime.datetime:
        if self._sleep is not MISSING:
            return self._last_iteration + datetime.timedelta(seconds=self._sleep)

        if self._time_index >= len(self._time):
            self._time_index = 0
            if self._current_loop == 0:
                # if we're at the last index on the first iteration, we need to sleep until tomorrow
                return datetime.datetime.combine(
                    datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1), self._time[0]
                )

        next_time = self._time[self._time_index]

        if self._current_loop == 0:
            self._time_index += 1
            if next_time > datetime.datetime.now(datetime.timezone.utc).timetz():
                return datetime.datetime.combine(datetime.datetime.now(datetime.timezone.utc), next_time)
            else:
                return datetime.datetime.combine(
                    datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1), next_time)

        next_date = cast(datetime.datetime, self._last_iteration)
        if next_time < next_date.timetz():
            next_date += datetime.timedelta(days=1)

        self._time_index += 1
        return datetime.datetime.combine(next_date, next_time)

    def _prepare_time_index(self, now: datetime.datetime = MISSING) -> None:
        # now kwarg should be a datetime.datetime representing the time "now"
        # to calculate the next time index from

        # pre-condition: self._time is set
        time_now = (
            now if now is not MISSING else datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
        ).timetz()
        for idx, time in enumerate(self._time):
            if time >= time_now:
                self._time_index = idx
                break
        else:
            self._time_index = 0

    def _get_time_parameter(
            self,
            time: Union[datetime.time, Sequence[datetime.time]],
            *,
            dt: Type[datetime.time] = datetime.time,
            utc: datetime.timezone = datetime.timezone.utc,
    ) -> List[datetime.time]:
        if isinstance(time, dt):
            inner = time if time.tzinfo is not None else time.replace(tzinfo=utc)
            return [inner]
        if not isinstance(time, Sequence):
            raise TypeError(
                f'预期 ``datetime.time`` 或 ``time`` 的一系列 ``datetime.time`` ，而是收到 {type(time)!r}。'
            )
        if not time:
            raise ValueError('时间参数不能是空序列。')

        ret: List[datetime.time] = []
        for index, t in enumerate(time):
            if not isinstance(t, dt):
                raise TypeError(
                    f'预期 ``time`` 的 {dt!r} 序列，而是在索引 {index} 处收到 {type(t).__name__!r} 。'
                )
            ret.append(t if t.tzinfo is not None else t.replace(tzinfo=utc))

        ret = sorted(set(ret))  # de-dupe and sort times
        return ret

    def change_interval(
            self,
            *,
            seconds: float = 0,
            minutes: float = 0,
            hours: float = 0,
            time: Union[datetime.time, Sequence[datetime.time]] = MISSING,
    ) -> None:
        """更改时间的间隔。

        Parameters
        ------------
        seconds: :class:`float`
            每次迭代之间的秒数。
        minutes: :class:`float`
            每次迭代之间的分钟数。
        hours: :class:`float`
            每次迭代之间的小时数。
        time: Union[:class:`datetime.time`, Sequence[:class:`datetime.time`]]
            运行此循环的确切时间。应该传递非空列表或 :class:`datetime.time` 的单个值。这不能与相对时间参数一起使用。

            .. note::

                重复次数将被忽略，并且只运行一次。

        Raises
        -------
        ValueError
            给出了无效值。
        TypeError
            传递了 ``time`` 参数的无效值，或者 ``time`` 参数与相对时间参数一起传递。
        """

        if time is MISSING:
            seconds = seconds or 0
            minutes = minutes or 0
            hours = hours or 0
            sleep = seconds + (minutes * 60.0) + (hours * 3600.0)
            if sleep < 0:
                raise ValueError('总秒数不能小于零。')

            self._sleep = sleep
            self._seconds = float(seconds)
            self._hours = float(hours)
            self._minutes = float(minutes)
            self._time: List[datetime.time] = MISSING
        else:
            if any((seconds, minutes, hours)):
                raise TypeError('不能将显式时间与相对时间混合')
            self._time = self._get_time_parameter(time)
            self._sleep = self._seconds = self._minutes = self._hours = MISSING

        if self.is_running():
            if self._time is not MISSING:
                # prepare the next time index starting from after the last iteration
                self._prepare_time_index(now=self._last_iteration)

            self._next_iteration = self._get_next_sleep_time()
            if self._handle and not self._handle.done():
                # the loop is sleeping, recalculate based on new interval
                self._handle.recalculate(self._next_iteration)


def loop(
        *,
        seconds: float = MISSING,
        minutes: float = MISSING,
        hours: float = MISSING,
        time: Union[datetime.time, Sequence[datetime.time]] = MISSING,
        count: Optional[int] = None,
        reconnect: bool = True,
        loop: asyncio.AbstractEventLoop = MISSING,
) -> Callable[[LF], Loop[LF]]:
    """使用可选的重新连接逻辑在后台为你安排任务的装饰器。装饰器返回一个 :class:`Loop`。

    Parameters
    ------------
    seconds: :class:`float`
        每次迭代之间的秒数。
    minutes: :class:`float`
        每次迭代之间的分钟数。
    hours: :class:`float`
        每次迭代之间的小时数。
    time: Union[:class:`datetime.time`, Sequence[:class:`datetime.time`]]
        运行此循环的确切时间。应该传递一个非空列表或一个 :class:`datetime.time` 的值。支持时区。
        如果没有给出时间的时区，则假定它代表 UTC 时间。这不能与相对时间参数结合使用。

        .. note::

            重复时间将被忽略，并且只运行一次。

    count: Optional[:class:`int`]
        要执行的循环次数，如果它应该是无限循环，则为“无”。
    reconnect: :class:`bool`
        是否使用类似于 ``qq.Client.connect`` 中使用的指数退避算法处理错误并重新启动任务。
    loop: :class:`asyncio.AbstractEventLoop`
        用于注册任务的循环，如果没有给出，则默认为 :func:`asyncio.get_event_loop`。

    Raises
    --------
    ValueError
        给出了无效值。
    TypeError
        该函数不是协程，传递的 ``time`` 参数的值无效，或者 ``time`` 参数与相对时间参数一起传递。
    """

    def decorator(func: LF) -> Loop[LF]:
        return Loop[LF](
            func,
            seconds=seconds,
            minutes=minutes,
            hours=hours,
            count=count,
            time=time,
            reconnect=reconnect,
            loop=loop,
        )

    return decorator
