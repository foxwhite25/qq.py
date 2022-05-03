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

__all__ = (
    'Client',
)

import asyncio
import logging
import signal
import sys
import traceback
from typing import Optional, Any, Dict, Callable, List, Tuple, Coroutine, TypeVar, Generator, Union, TYPE_CHECKING, \
    Sequence

import aiohttp

from . import utils
from .backoff import ExponentialBackoff
from .error import HTTPException, GatewayNotFound, ConnectionClosed
from .gateway import QQWebSocket, ReconnectWebSocket
from .guild import Guild
from .http import HTTPClient
from .iterators import GuildIterator
from .state import ConnectionState
from .user import ClientUser, User

if TYPE_CHECKING:
    from .guild import GuildChannel
    from .channel import DMChannel
    from .member import Member
    from .message import Message

URL = r'https://api.sgroup.qq.com'
_log = logging.getLogger(__name__)
Coro = TypeVar('Coro', bound=Callable[..., Coroutine[Any, Any, Any]])


def _cancel_tasks(loop: asyncio.AbstractEventLoop) -> None:
    tasks = {t for t in asyncio.all_tasks(loop=loop) if not t.done()}

    if not tasks:
        return

    _log.info('在 %d 个任务后清理。', len(tasks))
    for task in tasks:
        task.cancel()

    loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
    _log.info('所有任务都取消了。')

    for task in tasks:
        if task.cancelled():
            continue
        if task.exception() is not None:
            loop.call_exception_handler({
                'message': 'Client.run 关闭期间未处理的异常。',
                'exception': task.exception(),
                'task': task
            })


def _cleanup_loop(loop: asyncio.AbstractEventLoop) -> None:
    try:
        _cancel_tasks(loop)
        loop.run_until_complete(loop.shutdown_asyncgens())
    finally:
        _log.info('关闭事件循环。')
        loop.close()


class Client:
    r"""代表了客户端与 QQ 之间的连接
    此类用于与 QQ WebSocket 和 API 进行交互。
    许多选项可以传递给 :class:`Client`。

    Parameters
    -----------
    max_messages: Optional[:class:`int`]
        要存储在内部消息缓存中的最大消息数。
        这默认为 ``1000`` 。传入 ``None`` 会禁用消息缓存。
    loop: Optional[:class:`asyncio.AbstractEventLoop`]
        用于异步操作的 :class:`asyncio.AbstractEventLoop` 。
        默认为 ``None`` ，在这种情况下，默认事件循环通过 :func:`asyncio.get_event_loop()` 使用。
    connector: Optional[:class:`aiohttp.BaseConnector`]
        用于连接池的连接器。
    proxy: Optional[:class:`str`]
        代理网址。
    proxy_auth: Optional[:class:`aiohttp.BasicAuth`]
        代表代理 HTTP 基本授权的对象。
    shard_id: Optional[:class:`int`]
        从 0 开始并且小于 :attr:`.shard_count` 的整数。
    shard_count: Optional[:class:`int`]
        分片总数。
    intents: :class:`Intents`
        你要为会话启用的意图。 这是一种禁用和启用某些网关事件触发和发送的方法。
         如果未给出，则默认为默认的 Intents 类。
    heartbeat_timeout: :class:`float`
        在未收到 HEARTBEAT_ACK 的情况下超时和重新启动 WebSocket 之前的最大秒数。
        如果处理初始数据包花费的时间太长而导致你断开连接，则很有用。默认超时为 59 秒。
    guild_ready_timeout: :class:`float`
        在准备成员缓存和触发 READY 之前等待 GUILD_CREATE 流结束的最大秒数。默认超时为 2 秒。

    Attributes
    -----------
    ws
        客户端当前连接到的 websocket 网关。可能是 ``None`` 。
    loop: :class:`asyncio.AbstractEventLoop`
        客户端用于异步操作的事件循环。
    """

    def __init__(
            self,
            *,
            loop: Optional[asyncio.AbstractEventLoop] = None,
            **options: Any,
    ):
        self.ws: QQWebSocket = None  # type: ignore
        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop() if loop is None else loop
        self._listeners: Dict[str, List[Tuple[asyncio.Future, Callable[..., bool]]]] = {}
        self.token = ""
        self.shard_id: Optional[int] = options.get('shard_id')
        self.shard_count: Optional[int] = options.get('shard_count')
        self._enable_debug_events: bool = options.pop('enable_debug_events', False)

        self._handlers: Dict[str, Callable] = {
            'ready': self._handle_ready
        }

        self._hooks: Dict[str, Callable] = {
            'before_identify': self._call_before_identify_hook
        }

        connector: Optional[aiohttp.BaseConnector] = options.pop('connector', None)
        proxy: Optional[str] = options.pop('proxy', None)
        proxy_auth: Optional[aiohttp.BasicAuth] = options.pop('proxy_auth', None)
        unsync_clock: bool = options.pop('assume_unsync_clock', True)
        self.http: HTTPClient = HTTPClient(connector, proxy=proxy, proxy_auth=proxy_auth, unsync_clock=unsync_clock,
                                           loop=self.loop)

        self._connection: ConnectionState = self._get_state(**options)
        self._connection.shard_count = self.shard_count
        self._closed: bool = False
        self._ready: asyncio.Event = asyncio.Event()

    def _get_websocket(self, guild_id: Optional[int] = None, *, shard_id: Optional[int] = None) -> QQWebSocket:
        return self.ws

    def _get_state(self, **options: Any) -> ConnectionState:
        return ConnectionState(dispatch=self.dispatch, handlers=self._handlers,
                               hooks=self._hooks, http=self.http, loop=self.loop, **options)

    def _handle_ready(self) -> None:
        self._ready.set()

    async def _call_before_identify_hook(self, shard_id: Optional[int], *, initial: bool = False) -> None:
        # This hook is an internal hook that actually calls the public one.
        # It allows the library to have its own hook without stepping on the
        # toes of those who need to override their own hook.
        await self.before_identify_hook(shard_id, initial=initial)

    async def before_identify_hook(self, shard_id: Optional[int], *, initial: bool = False) -> None:
        if not initial:
            await asyncio.sleep(5.0)

    async def on_error(self, event_method: str, *args: Any, **kwargs: Any) -> None:
        """|coro|
        客户端提供的默认错误处理程序。
        默认情况下，这会打印到 :data:`sys.stderr` 但是它可以被覆盖以使用不同的实现。
        看看 :func:`~qq.on_error` 以获取更多详细信息。
        """

        print(f'忽略 {event_method} 中的异常', file=sys.stderr)
        traceback.print_exc()

    async def _run_event(self, coro: Callable[..., Coroutine[Any, Any, Any]], event_name: str, *args: Any,
                         **kwargs: Any) -> None:
        try:
            await coro(*args, **kwargs)
        except asyncio.CancelledError:
            pass
        except Exception:
            try:
                await self.on_error(event_name, *args, **kwargs)
            except asyncio.CancelledError:
                pass

    def _schedule_event(self, coro: Callable[..., Coroutine[Any, Any, Any]], event_name: str, *args: Any,
                        **kwargs: Any) -> asyncio.Task:
        wrapped = self._run_event(coro, event_name, *args, **kwargs)
        # Schedules the task
        return asyncio.create_task(wrapped, name=f'qq.py: {event_name}')

    def dispatch(self, event: str, *args: Any, **kwargs: Any) -> None:
        _log.debug('分派事件 %s', event)
        method = 'on_' + event

        listeners = self._listeners.get(event)
        if listeners:
            removed = []
            for i, (future, condition) in enumerate(listeners):
                if future.cancelled():
                    removed.append(i)
                    continue

                try:
                    result = condition(*args)
                except Exception as exc:
                    future.set_exception(exc)
                    removed.append(i)
                else:
                    if result:
                        if len(args) == 0:
                            future.set_result(None)
                        elif len(args) == 1:
                            future.set_result(args[0])
                        else:
                            future.set_result(args)
                        removed.append(i)

            if len(removed) == len(listeners):
                self._listeners.pop(event)
            else:
                for idx in reversed(removed):
                    del listeners[idx]

        try:
            coro = getattr(self, method)
        except AttributeError:
            pass
        else:
            self._schedule_event(coro, method, *args, **kwargs)

    async def login(self, token: str) -> None:
        """|coro|
        使用指定的凭据登录客户端。

        Parameters
        -----------
        token: :class:`str`
            身份验证令牌。不要在这个令牌前面加上任何东西，因为库会为你做这件事。

        Raises
        ------
        :exc:`.LoginFailure`
            传递了错误的凭据。
        :exc:`.HTTPException`
            发生未知的 HTTP 相关错误，通常是当它不是 200 或已知的错误。
        """
        _log.info('使用静态令牌登录')
        self.token = token
        data = await self.http.static_login(token.strip())
        self._connection.user = ClientUser(state=self._connection, data=data)

    @property
    def latency(self) -> float:
        """:class:`float`: 以秒为单位测量 HEARTBEAT 和 HEARTBEAT_ACK 之间的延迟。这可以称为 QQ WebSocket 协议延迟。
        """
        ws = self.ws
        return float('nan') if not ws else ws.latency

    def is_ready(self) -> bool:
        """:class:`bool`: 指定客户端的内部缓存是否可以使用。"""
        return self._ready.is_set()

    @property
    def user(self) -> Optional[ClientUser]:
        """Optional[:class:`.ClientUser`]: 代表连接的客户端。如果未登录，则为 ``None`` 。"""
        return self._connection.user

    @property
    def guilds(self) -> List[Guild]:
        """List[:class:`.Guild`]: 连接的客户端所属的频道。"""
        return self._connection.guilds

    @property
    def cached_messages(self) -> Sequence[Message]:
        """Sequence[:class:`.Message`]: 连接的客户端已缓存的消息的只读列表。
        """
        return utils.SequenceProxy(self._connection._messages or [])

    def get_guild(self, id: int, /) -> Optional[Guild]:
        """返回具有给定 ID 的频道。

        Parameters
        -----------
        id: :class:`int`
            要搜索的 ID。

        Returns
        --------
        Optional[:class:`.Guild`]
            如果未找到频道则 ``None`` 。
        """
        return self._connection._get_guild(id)

    def get_user(self, id: int, /) -> Optional[User]:
        """返回具有给定 ID 的用户。

        Parameters
        -----------
        id: :class:`int`
            要搜索的 ID。

        Returns
        --------
        Optional[:class:`~qq.User`]
            如果未找到，则为 ``None`` 。
        """
        return self._connection.get_user(id)

    async def fetch_guild(self, guild_id: int) -> Optional[Guild]:
        """|coro|

        从 ID 中检索 :class:`.Guild` 。

        .. note::

            使用它，你将 **不会** 收到 :attr:`.Guild.channels` 、 :attr:`.Guild.members` 。

        .. note::

            此方法是 API 调用。对于一般用法，请考虑 :meth:`get_guild` 。

        Parameters
        -----------
        guild_id: :class:`int`
            要从中获取的频道 ID。

        Raises
        ------
        :exc:`.Forbidden`
            你无权访问频道。
        :exc:`.HTTPException`
            获得频道失败。

        Returns
        --------
        :class:`.Guild`
            来自ID的频道。
        """
        data = await self.http.get_guild(guild_id)
        return Guild(data=data, state=self._connection)

    async def fetch_guilds(
            self,
            *,
            limit: Optional[int] = 100,
    ):
        """获得一个 :class:`.AsyncIterator` 来接收你的频道。

        .. note::

            该方法是一个 API 调用。对于一般用法，请考虑 :attr:`guilds`。

        Examples
        ---------
        用法 ::

            async for guild in client.fetch_guilds(limit=150):
                print(guild.name)

        展平成一个列表 ::
        
            guilds = await client.fetch_guilds(limit=150).flatten()
            # guilds is now a list of Guild...
        
        所有参数都是可选的。
        
        Parameters
        -----------
        limit: Optional[:class:`int`]
            要检索的频道数量。如果为 ``None`` ，它将检索你有权访问的每个频道。但是请注意，这会使其操作变慢。默认为“100”。
        
        Raises
        ------
        :exc:`.HTTPException`
            获取频道失败。
        
        Yields
        --------
        :class:`.Guild`
            已解析频道数据的频道。
        """

        return GuildIterator(self, limit=limit)

    def run(self, *args: Any, **kwargs: Any) -> None:
        """一个阻塞调用，它从你那里抽象出事件循环初始化。
        如果你想对事件循环进行更多控制，则不应使用此函数。使用 :meth:`start` 协程或 :meth:`connect` + :meth:`login`。

        大致相当于： ::

            try:
                loop.run_until_complete(start(*args, **kwargs))
            except KeyboardInterrupt:
                loop.run_until_complete(close())
                # cancel all tasks lingering
            finally:
                loop.close()

        .. warning::

            由于它是阻塞的，因此该函数必须是最后一个调用的函数。
            这意味着在此函数调用之后注册的事件或任何被调用的东西在它返回之前不会执行。

        """
        loop = self.loop

        try:
            loop.add_signal_handler(signal.SIGINT, lambda: loop.stop())
            loop.add_signal_handler(signal.SIGTERM, lambda: loop.stop())
        except NotImplementedError:
            pass

        async def runner():
            try:
                await self.start(**kwargs)
            finally:
                if not self.is_closed():
                    await self.close()

        def stop_loop_on_completion(f):
            loop.stop()

        future = asyncio.ensure_future(runner(), loop=loop)
        future.add_done_callback(stop_loop_on_completion)
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            _log.info('接收到终止机器人和事件循环的信号。')
        finally:
            future.remove_done_callback(stop_loop_on_completion)
            _log.info('清理任务。')
            _cleanup_loop(loop)

        if not future.cancelled():
            try:
                return future.result()
            except KeyboardInterrupt:
                # I am unsure why this gets raised here but suppress it anyway
                return None

    async def start(self, token: str, reconnect: bool = True) -> None:
        """|coro|
        :meth:`login` + :meth:`connect` 的协程。

        Raises
        -------
        TypeError
            收到意外的关键字参数。
        """
        await self.login(token)
        await self.connect(reconnect=reconnect)

    def clear(self) -> None:
        """清除机器人的内部状态。在此之后，机器人可以被视为 ``重新连接`` ，
        即 :meth:`is_closed` 和 :meth:`is_ready` 都返回 ``False`` 以及清除机器人的内部缓存。
        """
        self._closed = False
        self._ready.clear()
        self._connection.clear()
        self.http.recreate()

    def is_closed(self) -> bool:
        """:class:`bool`: 指示 websocket 连接是否关闭。"""
        return self._closed

    async def connect(self, *, reconnect: bool = True) -> None:
        """|coro|
        创建一个 websocket 连接并让 websocket 监听来自 QQ 的消息。这运行整个事件系统和库的其他方面的循环。在 WebSocket 连接终止之前，不会恢复控制。

        Parameters
        -----------
        reconnect: :class:`bool`
            我们应不应该尝试重新连接，无论是由于互联网故障还是 QQ 的特定故障。
            某些导致错误状态的断开连接将不会得到处理（例如无效的分片或错误的令牌）。

        Raises
        -------
        :exc:`.GatewayNotFound`
            如果找不到连接到 QQ 的网关。通常，如果抛出此问题，则会导致 QQ API 中断。
        :exc:`.ConnectionClosed`
            websocket 连接已终止。
        """
        backoff = ExponentialBackoff()
        ws_params = {
            'initial': True,
            'shard_id': self.shard_id,
        }
        while not self.is_closed():
            try:
                coro = QQWebSocket.from_client(self, **ws_params)
                self.ws = await asyncio.wait_for(coro, timeout=60.0)
                ws_params['initial'] = False
                while True:
                    await self.ws.poll_event()
            except ReconnectWebSocket as e:
                _log.info('收到了 %s websocket 的请求。', e.op)
                self.dispatch('disconnect')
                ws_params.update(sequence=self.ws.sequence, resume=e.resume, session=self.ws.session_id)
                continue
            except (OSError,
                    HTTPException,
                    GatewayNotFound,
                    ConnectionClosed,
                    aiohttp.ClientError,
                    asyncio.TimeoutError) as exc:

                self.dispatch('disconnect')
                if not reconnect:
                    await self.close()
                    if isinstance(exc, ConnectionClosed) and exc.code == 1000:
                        # clean close, don't re-raise this
                        return
                    raise

                if self.is_closed():
                    return

                # If we get connection reset by peer then try to RESUME
                if isinstance(exc, OSError) and exc.errno in (54, 10054):
                    ws_params.update(sequence=self.ws.sequence, initial=False, resume=True, session=self.ws.session_id)
                    continue

                # We should only get this when an unhandled close code happens,
                # such as a clean disconnect (1000) or a bad state (bad token, no sharding, etc)
                # sometimes, qq sends us 1000 for unknown reasons, so we should reconnect
                # regardless and rely on is_closed instead
                if isinstance(exc, ConnectionClosed):
                    if exc.code != 1000:
                        await self.close()
                        raise

                retry = backoff.delay()
                _log.exception("尝试在 %.2fs 中重新连接", retry)
                await asyncio.sleep(retry)
                # Always try to RESUME the connection
                # If the connection is not RESUME-able then the gateway will invalidate the session.
                # This is apparently what the official qq client does.
                ws_params.update(sequence=self.ws.sequence, resume=True, session=self.ws.session_id)

    async def close(self) -> None:
        """|coro|
        关闭与 QQ 的连接。
        """
        if self._closed:
            return

        self._closed = True

        if self.ws is not None and self.ws.open:
            await self.ws.close(code=1000)

        await self.http.close()
        self._ready.clear()

    def get_channel(self, id: int, /) -> Optional[Union[GuildChannel]]:
        """返回具有给定 ID 的子频道。
        Parameters
        -----------
        id: :class:`int`
            要搜索的 ID。
        Returns
        --------
        Optional[Union[:class:`.abc.GuildChannel`, :class:`.Thread`, :class:`.abc.PrivateChannel`]]
            返回的子频道或 ``None``（如果未找到）。
        """
        return self._connection.get_channel(id)

    def get_all_channels(self) -> Generator[GuildChannel, None, None]:
        """一个生成器，它检索客户端可以“访问”的每个 :class:`.abc.GuildChannel`。

        这相当于： ::

            for guild in client.guilds:
                for channel in guild.channels:
                    yield channel

        Yields
        ------
        :class:`.abc.GuildChannel`
            客户端可以“访问”的子频道。
        """

        for guild in self.guilds:
            yield from guild.channels

    def get_all_members(self) -> Generator[Member, None, None]:
        """返回一个生成器，其中包含客户端可以看到的每个 :class:`.Member`。

        这相当于： ::

            for guild in client.guilds:
                for member in guild.members:
                    yield member

        Yields
        ------
        :class:`.Member`
            客户端可以看到的成员。
        """
        for guild in self.guilds:
            yield from guild.members

    async def wait_until_ready(self) -> None:
        """|coro|
        等到客户端的内部缓存准备就绪。
        """
        await self._ready.wait()

    def wait_for(
            self,
            event: str,
            *,
            check: Optional[Callable[..., bool]] = None,
            timeout: Optional[float] = None,
    ) -> Any:
        """|coro|
        等待调度 WebSocket 事件。 这可用于等待用户回复消息，或对消息做出反应，或以独立的方式编辑消息。
        ``timeout`` 参数传递给 :func:`asyncio.wait_for`。
        默认情况下，它不会超时。 请注意，为了便于使用这在超时的时候会传播 :exc:`asyncio.TimeoutError` 。
        如果事件返回多个参数，则返回包含这些参数的 :class:`tuple` 。 请查看 :ref:`文档 <qq-api-events>` 以获取事件列表及其参数。
        该函数返回 **第一个符合要求的事件** 。

        Examples
        ---------
        等待用户回复： ::

            @client.event
            async def on_message(message):
                if message.content.startswith('$greet'):
                    channel = message.channel
                    await channel.send('Say hello!')
                    def check(m):
                        return m.content == 'hello' and m.channel == channel
                    msg = await client.wait_for('message', check=check)
                    await channel.send(f'Hello {msg.author}!')

        等待消息作者的 reaction ： ::

            @client.event
            async def on_message(message):
                if message.content.startswith('$thumb'):
                    channel = message.channel
                    def check(reaction, user):
                        return user == message.author
                    try:
                        reaction, user = await client.wait_for('reaction_add', timeout=60.0, check=check)
                    except asyncio.TimeoutError:
                        await channel.send('Got it')
                    else:
                        await channel.send('Time out')

        Parameters
        ------------
        event: :class:`str`
            事件名称，类似于 :ref:`事件指南 <qq-api-events>`，但没有 ``on_`` 前缀，用于等待。
        check: Optional[Callable[..., :class:`bool`]]
            检查等待什么的检查函数。 参数必须满足正在等待的事件的参数。
        timeout: Optional[:class:`float`]
            在超时和引发 :exc:`asyncio.TimeoutError` 之前等待的秒数。

        Raises
        -------
        asyncio.TimeoutError
            如果提供超时并且已达到。

        Returns
        --------
        Any
            不返回任何参数、单个参数或多个参数的元组，
            这些参数反映在 :ref:`事件指南 <qq-api-events>` 中传递的参数。
        """

        future = self.loop.create_future()
        if check is None:
            def _check(*args):
                return True

            check = _check

        ev = event.lower()
        try:
            listeners = self._listeners[ev]
        except KeyError:
            listeners = []
            self._listeners[ev] = listeners

        listeners.append((future, check))
        return asyncio.wait_for(future, timeout)

    def event(self, coro: Coro) -> Coro:
        """注册要监听的事件的装饰器。
        你可以在 :ref:`下面的文档 <qq-api-events>` 上找到有关事件的更多信息.
        事件必须是 :ref:`协程 <coroutine>` ，如果不是，则引发 :exc:`TypeError` 。

        Example
        ---------
        .. code-block:: python3

            @client.event
            async def on_ready():
            print('Ready!')


        Raises
        --------
        TypeError
            coro 需要是协程但实际上并不是协程。
        """

        if not asyncio.iscoroutinefunction(coro):
            raise TypeError('注册的事件必须是协程函数')

        setattr(self, coro.__name__, coro)
        _log.debug('%s 已成功注册为事件', coro.__name__)
        return coro

    async def create_dm(self, user: User, guild: Guild) -> DMChannel:
        """|coro|
        用这个用户创建一个 :class:`.DMChannel`。
        这应该很少被调用，因为这对大多数人来说都不需要用到的。

        Parameters
        -----------
        user: :class:`~qq.User`
            用于创建私信的用户。
        guild: :class: `~qq.Guild`
            用于创建私信的源频道

        Returns
        -------
        :class:`.DMChannel`
            创建的频道。
        """
        state = self._connection
        found = state._get_private_channel_by_user(user.id)
        if found:
            return found

        data = await state.http.start_private_message(user.id, guild.id)
        return state.add_dm_channel(data, user)
