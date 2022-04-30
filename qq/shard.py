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
import logging
from typing import TYPE_CHECKING, Any, Callable, Tuple, Type, Optional, List, Dict, TypeVar

import aiohttp

from .backoff import ExponentialBackoff
from .client import Client
from .error import (
    ClientException,
    HTTPException,
    GatewayNotFound,
    ConnectionClosed,
)
from .gateway import *
from .state import AutoShardedConnectionState

if TYPE_CHECKING:
    from .gateway import QQWebSocket

    EI = TypeVar('EI', bound='EventItem')

__all__ = (
    'AutoShardedClient',
    'ShardInfo',
)

_log = logging.getLogger(__name__)


class EventType:
    close = 0
    reconnect = 1
    resume = 2
    identify = 3
    terminate = 4
    clean_close = 5


class EventItem:
    __slots__ = ('type', 'shard', 'error')

    def __init__(self, etype: int, shard: Optional['Shard'], error: Optional[Exception]) -> None:
        self.type: int = etype
        self.shard: Optional['Shard'] = shard
        self.error: Optional[Exception] = error

    def __lt__(self: EI, other: EI) -> bool:
        if not isinstance(other, EventItem):
            return NotImplemented
        return self.type < other.type

    def __eq__(self: EI, other: EI) -> bool:
        if not isinstance(other, EventItem):
            return NotImplemented
        return self.type == other.type

    def __hash__(self) -> int:
        return hash(self.type)


class Shard:
    def __init__(self, ws: QQWebSocket, client: AutoShardedClient, queue_put: Callable[[EventItem], None]) -> None:
        self.ws: QQWebSocket = ws
        self._client: Client = client
        self._dispatch: Callable[..., None] = client.dispatch
        self._queue_put: Callable[[EventItem], None] = queue_put
        self.loop: asyncio.AbstractEventLoop = self._client.loop
        self._disconnect: bool = False
        self._reconnect = client._reconnect
        self._backoff: ExponentialBackoff = ExponentialBackoff()
        self._task: Optional[asyncio.Task] = None
        self._handled_exceptions: Tuple[Type[Exception], ...] = (
            OSError,
            HTTPException,
            GatewayNotFound,
            ConnectionClosed,
            aiohttp.ClientError,
            asyncio.TimeoutError,
        )

    @property
    def id(self) -> int:
        # QQWebSocket.shard_id is set in the from_client classmethod
        return self.ws.shard_id  # type: ignore

    def launch(self) -> None:
        self._task = self.loop.create_task(self.worker())

    def _cancel_task(self) -> None:
        if self._task is not None and not self._task.done():
            self._task.cancel()

    async def close(self) -> None:
        self._cancel_task()
        await self.ws.close(code=1000)

    async def disconnect(self) -> None:
        await self.close()
        self._dispatch('shard_disconnect', self.id)

    async def _handle_disconnect(self, e: Exception) -> None:
        self._dispatch('disconnect')
        self._dispatch('shard_disconnect', self.id)
        if not self._reconnect:
            self._queue_put(EventItem(EventType.close, self, e))
            return

        if self._client.is_closed():
            return

        if isinstance(e, OSError) and e.errno in (54, 10054):
            # If we get Connection reset by peer then always try to RESUME the connection.
            exc = ReconnectWebSocket(self.id, resume=True)
            self._queue_put(EventItem(EventType.resume, self, exc))
            return

        if isinstance(e, ConnectionClosed):
            if e.code != 1000:
                self._queue_put(EventItem(EventType.close, self, e))
                return

        retry = self._backoff.delay()
        _log.error('正在 %.2fs 后尝试重新连接分片ID %s',retry , self.id, exc_info=e)
        await asyncio.sleep(retry)
        self._queue_put(EventItem(EventType.reconnect, self, e))

    async def worker(self) -> None:
        while not self._client.is_closed():
            try:
                await self.ws.poll_event()
            except ReconnectWebSocket as e:
                etype = EventType.resume if e.resume else EventType.identify
                self._queue_put(EventItem(etype, self, e))
                break
            except self._handled_exceptions as e:
                await self._handle_disconnect(e)
                break
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._queue_put(EventItem(EventType.terminate, self, e))
                break

    async def reidentify(self, exc: ReconnectWebSocket) -> None:
        self._cancel_task()
        self._dispatch('disconnect')
        self._dispatch('shard_disconnect', self.id)
        _log.info('Shard ID %s 收到对 %s websocket 的请求。', exc.op, self.id)
        try:
            coro = QQWebSocket.from_client(
                self._client,
                resume=exc.resume,
                shard_id=self.id,
                session=self.ws.session_id,
                sequence=self.ws.sequence,
            )
            self.ws = await asyncio.wait_for(coro, timeout=60.0)
        except self._handled_exceptions as e:
            await self._handle_disconnect(e)
        except asyncio.CancelledError:
            return
        except Exception as e:
            self._queue_put(EventItem(EventType.terminate, self, e))
        else:
            self.launch()

    async def reconnect(self) -> None:
        self._cancel_task()
        try:
            coro = QQWebSocket.from_client(self._client, shard_id=self.id)
            self.ws = await asyncio.wait_for(coro, timeout=60.0)
        except self._handled_exceptions as e:
            await self._handle_disconnect(e)
        except asyncio.CancelledError:
            return
        except Exception as e:
            self._queue_put(EventItem(EventType.terminate, self, e))
        else:
            self.launch()


class ShardInfo:
    """提供信息和控制特定分片的类。
    你可以通过 :meth:`AutoShardedClient.get_shard` 或 :attr:`AutoShardedClient.shards` 检索这个对象。

    Attributes
    ------------
    id: :class:`int`
        此分片的分片 ID。
    shard_count: Optional[:class:`int`]
        此集群的分片计数。如果这是 ``None`` ，则机器人尚未启动。
    """

    __slots__ = ('_parent', 'id', 'shard_count')

    def __init__(self, parent: Shard, shard_count: Optional[int]) -> None:
        self._parent: Shard = parent
        self.id: int = parent.id
        self.shard_count: Optional[int] = shard_count

    def is_closed(self) -> bool:
        """:class:`bool`: 分片连接当前是否关闭。"""
        return not self._parent.ws.open

    async def disconnect(self) -> None:
        """|coro|
        断开分片。当这个被调用时，分片连接将关闭。
        如果分片已经断开连接，则不会执行任何操作。
        """
        if self.is_closed():
            return

        await self._parent.disconnect()

    async def reconnect(self) -> None:
        """|coro|
        断开连接，然后再次连接分片。
        """
        if not self.is_closed():
            await self._parent.disconnect()
        await self._parent.reconnect()

    async def connect(self) -> None:
        """|coro|
        连接一个分片。如果分片已连接，则不会执行任何操作。
        """
        if not self.is_closed():
            return

        await self._parent.reconnect()

    @property
    def latency(self) -> float:
        """:class:`float`: 测量此分片的 HEARTBEAT 和 HEARTBEAT_ACK 之间的延迟（以秒为单位）。"""
        return self._parent.ws.latency

    def is_ws_ratelimited(self) -> bool:
        """:class:`bool`: websocket 当前是否有速率限制。
        """
        return self._parent.ws.is_ratelimited()


class AutoShardedClient(Client):
    """一个类似于 :class:`Client` 的客户端，
    只是它将用户分片的复杂性处理成一个更易于管理和透明的单进程机器人。
    当使用这个客户端时，你将能够像 :class:`Client` 一样使用它，就像它是一个带有单个分片的常规客户端，当在内部实现时，它被分成多个分片。
    这使你不必处理 IPC 或其他复杂的基础。
    建议人数超过1000人以上才使用此客户端。
    如果没有提供 :attr:`.shard_count`，则库将使用 Bot Gateway 端点调用来确定要使用多少个分片。
    如果给出了 ``shard_ids`` 参数，则这些分片 ID 将用于启动内部分片。
    请注意，如果使用 :attr:`.shard_count` ，则必须提供。默认情况下，当省略时，客户端将启动从 0 到 ``shard_count - 1`` 的分片。

    Attributes
    ------------
    shard_ids: Optional[List[:class:`int`]]
        用于启动分片的可选 shard_id 列表。
    """

    if TYPE_CHECKING:
        _connection: AutoShardedConnectionState

    def __init__(self, *args: Any, loop: Optional[asyncio.AbstractEventLoop] = None, **kwargs: Any) -> None:
        kwargs.pop('shard_id', None)
        self.shard_ids: Optional[List[int]] = kwargs.pop('shard_ids', None)
        super().__init__(*args, loop=loop, **kwargs)

        if self.shard_ids is not None:
            if self.shard_count is None:
                raise ClientException('在传递手动 shard_ids 时，你必须提供一个 shard_count。')
            elif not isinstance(self.shard_ids, (list, tuple)):
                raise ClientException('shard_ids 参数必须是列表或元组。')

        # instead of a single websocket, we have multiple
        # the key is the shard_id
        self.__shards = {}
        self._connection._get_websocket = self._get_websocket
        self._connection._get_client = lambda: self
        self.__queue = asyncio.PriorityQueue()

    def _get_websocket(self, guild_id: Optional[int] = None, *, shard_id: Optional[int] = None) -> QQWebSocket:
        if shard_id is None:
            # guild_id won't be None if shard_id is None and shard_count won't be None here
            shard_id = (guild_id >> 22) % self.shard_count  # type: ignore
        return self.__shards[shard_id].ws

    def _get_state(self, **options: Any) -> AutoShardedConnectionState:
        return AutoShardedConnectionState(
            dispatch=self.dispatch,
            handlers=self._handlers,
            hooks=self._hooks,
            http=self.http,
            loop=self.loop,
            **options,
        )

    @property
    def latency(self) -> float:
        """:class:`float`: 以秒为单位测量 HEARTBEAT 和 HEARTBEAT_ACK 之间的延迟。
        这与 :meth:`Client.latency` 的操作类似，但是它使用每个分片延迟的平均延迟。
        要获取分片延迟列表，请检查 :attr:`latencies` 属性。如果没有分片，则返回 ``nan`` 。
        """
        if not self.__shards:
            return float('nan')
        return sum(latency for _, latency in self.latencies) / len(self.__shards)

    @property
    def latencies(self) -> List[Tuple[int, float]]:
        """List[Tuple[:class:`int`, :class:`float`]]: HEARTBEAT 和 HEARTBEAT_ACK 之间的延迟列表（以秒为单位）。
        这将返回一个包含元素 ``(shard_id, latency)`` 的元组列表。
        """
        return [(shard_id, shard.ws.latency) for shard_id, shard in self.__shards.items()]

    def get_shard(self, shard_id: int) -> Optional[ShardInfo]:
        """Optional[:class:`ShardInfo`]: 获取给定分片 ID 的分片信息，如果未找到则为 ``None`` 。"""
        try:
            parent = self.__shards[shard_id]
        except KeyError:
            return None
        else:
            return ShardInfo(parent, self.shard_count)

    @property
    def shards(self) -> Dict[int, ShardInfo]:
        """Mapping[int, :class:`ShardInfo`]: 返回分片 ID 到其各自信息对象的映射。"""
        return {shard_id: ShardInfo(parent, self.shard_count) for shard_id, parent in self.__shards.items()}

    async def launch_shard(self, gateway: str, shard_id: int, *, initial: bool = False) -> None:
        try:
            coro = QQWebSocket.from_client(self, initial=initial, gateway=gateway, shard_id=shard_id)
            ws = await asyncio.wait_for(coro, timeout=180.0)
        except Exception:
            _log.exception('无法连接 shard_id: %s。正在重试...', shard_id)
            await asyncio.sleep(5.0)
            return await self.launch_shard(gateway, shard_id)

        # keep reading the shard while others connect
        self.__shards[shard_id] = ret = Shard(ws, self, self.__queue.put_nowait)
        ret.launch()

    async def launch_shards(self) -> None:
        if self.shard_count is None:
            self.shard_count, gateway = await self.http.get_bot_gateway()
        else:
            gateway = await self.http.get_gateway()

        self._connection.shard_count = self.shard_count

        shard_ids = self.shard_ids or range(self.shard_count)
        self._connection.shard_ids = shard_ids

        for shard_id in shard_ids:
            initial = shard_id == shard_ids[0]
            await self.launch_shard(gateway, shard_id, initial=initial)

        self._connection.shards_launched.set()

    async def connect(self, *, reconnect: bool = True) -> None:
        self._reconnect = reconnect
        await self.launch_shards()

        while not self.is_closed():
            item = await self.__queue.get()
            if item.type == EventType.close:
                await self.close()
                if isinstance(item.error, ConnectionClosed):
                    if item.error.code != 1000:
                        raise item.error
                return
            elif item.type in (EventType.identify, EventType.resume):
                await item.shard.reidentify(item.error)
            elif item.type == EventType.reconnect:
                await item.shard.reconnect()
            elif item.type == EventType.terminate:
                await self.close()
                raise item.error
            elif item.type == EventType.clean_close:
                return

    async def close(self) -> None:
        """|coro|
        关闭与 QQ 的连接。
        """
        if self.is_closed():
            return

        self._closed = True
        to_close = [asyncio.ensure_future(shard.close(), loop=self.loop) for shard in self.__shards.values()]
        if to_close:
            await asyncio.wait(to_close)

        await self.http.close()
        self.__queue.put_nowait(EventItem(EventType.clean_close, None, None))

    def is_ws_ratelimited(self) -> bool:
        """:class:`bool`: websocket 当前是否有速率限制。
        此实现检查是否有任何分片受速率限制。如需更精细的控制，请考虑 :meth:`ShardInfo.is_ws_ratelimited` 。
        """
        return any(shard.ws.is_ratelimited() for shard in self.__shards.values())
