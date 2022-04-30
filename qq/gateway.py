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

import asyncio
import concurrent
import logging
import sys
import threading
import time
import traceback
import zlib
from collections import namedtuple

import aiohttp

from qq import utils
from qq.error import ConnectionClosed

EventListener = namedtuple('EventListener', 'predicate event result future')
_log = logging.getLogger(__name__)

__all__ = (
    'QQWebSocket',
    'KeepAliveHandler',
    'QQClientWebSocketResponse',
    'ReconnectWebSocket',
)


class QQClientWebSocketResponse(aiohttp.ClientWebSocketResponse):
    async def close(self, *, code: int = 4000, message: bytes = b'') -> bool:
        return await super().close(code=code, message=message)


class WebSocketClosure(Exception):
    """一个来对付 aiohttp 不发出关闭信号的错误。"""
    pass


class ReconnectWebSocket(Exception):
    """安全地重新连接 websocket 的信号。"""

    def __init__(self, shard_id, *, resume=True):
        self.shard_id = shard_id
        self.resume = resume
        self.op = 'RESUME' if resume else 'IDENTIFY'


class KeepAliveHandler(threading.Thread):
    def __init__(self, *args, **kwargs):
        ws = kwargs.pop('ws', None)
        interval = kwargs.pop('interval', None)
        shard_id = kwargs.pop('shard_id', None)
        threading.Thread.__init__(self, *args, **kwargs)
        self.ws = ws
        self._main_thread_id = ws.thread_id
        self.interval = interval
        self.daemon = True
        self.shard_id = shard_id
        self.msg = '使用序列 %s 保持分片 ID %s websocket 处于活动状态。'
        self.block_msg = '分片 ID %s 心跳被阻止超过 %s 秒。'
        self.behind_msg = '跟不上，分片 ID %s websocket 落后 %.1fs。'
        self._stop_ev = threading.Event()
        self._last_ack = time.perf_counter()
        self._last_send = time.perf_counter()
        self._last_recv = time.perf_counter()
        self.latency = float('inf')
        self.heartbeat_timeout = ws._max_heartbeat_timeout

    def run(self):
        while not self._stop_ev.wait(self.interval):
            if self._last_recv + self.heartbeat_timeout < time.perf_counter():
                _log.warning("分片 ID %s 已停止响应 websocket 。关闭并重新启动。",
                             self.shard_id)
                coro = self.ws.close(4000)
                f = asyncio.run_coroutine_threadsafe(coro, loop=self.ws.loop)

                try:
                    f.result()
                except Exception:
                    _log.exception('停止 websocket 时发生错误。无视。')
                finally:
                    self.stop()
                    return

            data = self.get_payload()
            _log.debug(self.msg, data['d'], self.shard_id)
            coro = self.ws.send_heartbeat(data)
            f = asyncio.run_coroutine_threadsafe(coro, loop=self.ws.loop)
            try:
                # block until sending is complete
                total = 0
                while True:
                    try:
                        f.result(10)
                        break
                    except concurrent.futures.TimeoutError:
                        total += 10
                        try:
                            frame = sys._current_frames()[self._main_thread_id]
                        except KeyError:
                            msg = self.block_msg
                        else:
                            stack = ''.join(traceback.format_stack(frame))
                            msg = f'{self.block_msg}\nLoop 线程回溯（最近一次调用）：\n{stack}'
                        _log.warning(msg, self.shard_id, total)

            except Exception:
                self.stop()
            else:
                self._last_send = time.perf_counter()

    def get_payload(self):
        return {
            'op': self.ws.HEARTBEAT,
            'd': self.ws.sequence
        }

    def stop(self):
        self._stop_ev.set()

    def tick(self):
        self._last_recv = time.perf_counter()

    def ack(self):
        ack_time = time.perf_counter()
        self._last_ack = ack_time
        self.latency = ack_time - self._last_send
        if self.latency > 10:
            _log.warning(self.behind_msg, self.shard_id, self.latency)


class GatewayRatelimiter:
    def __init__(self, count=110, per=60.0):
        # The default is 110 to give room for at least 10 heartbeats per minute
        self.max = count
        self.remaining = count
        self.window = 0.0
        self.per = per
        self.lock = asyncio.Lock()
        self.shard_id = None

    def is_ratelimited(self):
        current = time.time()
        if current > self.window + self.per:
            return False
        return self.remaining == 0

    def get_delay(self):
        current = time.time()

        if current > self.window + self.per:
            self.remaining = self.max

        if self.remaining == self.max:
            self.window = current

        if self.remaining == 0:
            return self.per - (current - self.window)

        self.remaining -= 1
        if self.remaining == 0:
            self.window = current

        return 0.0

    async def block(self):
        async with self.lock:
            delta = self.get_delay()
            if delta:
                _log.warning('分片 ID %s 中的 WebSocket 受速率限制，等待 %.2f 秒', self.shard_id, delta)
                await asyncio.sleep(delta)


class QQWebSocket:
    DISPATCH = 0
    HEARTBEAT = 1
    IDENTIFY = 2
    PRESENCE = 3
    VOICE_STATE = 4
    VOICE_PING = 5
    RESUME = 6
    RECONNECT = 7
    REQUEST_MEMBERS = 8
    INVALIDATE_SESSION = 9
    HELLO = 10
    HEARTBEAT_ACK = 11
    GUILD_SYNC = 12

    def __init__(self, socket, *, loop):
        self.socket = socket
        self.loop = loop

        # an empty dispatcher to prevent crashes
        self._dispatch = lambda *args: None
        # generic event listeners
        self._dispatch_listeners = []
        # the keep alive
        self._keep_alive = None
        self.thread_id = threading.get_ident()

        # ws related stuff
        self.session_id = None
        self.sequence = None
        self._zlib = zlib.decompressobj()
        self._buffer = bytearray()
        self._close_code = None
        self._rate_limiter = GatewayRatelimiter()

    @property
    def open(self):
        return not self.socket.closed

    def is_ratelimited(self):
        return self._rate_limiter.is_ratelimited()

    def debug_log_receive(self, data, /):
        self._dispatch('socket_raw_receive', data)

    def log_receive(self, _, /):
        pass

    @classmethod
    async def from_client(cls, client, *, initial=False, gateway=None, shard_id=None, session=None, sequence=None,
                          resume=False):
        """从 :class:`Client` 为 qq 创建一个主 websocket。
        这仅供内部使用。
        """
        gateway = gateway or await client.http.get_gateway()
        socket = await client.http.ws_connect(gateway)
        ws = cls(socket, loop=client.loop)

        # dynamically add attributes needed
        ws.token = client.http.token
        ws._connection = client._connection
        ws._qq_parsers = client._connection.parsers
        ws._dispatch = client.dispatch
        ws.gateway = gateway
        ws.call_hooks = client._connection.call_hooks
        ws._initial_identify = initial
        ws.shard_id = shard_id
        ws._rate_limiter.shard_id = shard_id
        ws.shard_count = client._connection.shard_count
        ws.session_id = session
        ws.sequence = sequence
        ws._max_heartbeat_timeout = client._connection.heartbeat_timeout

        if client._enable_debug_events:
            ws.send = ws.debug_send
            ws.log_receive = ws.debug_log_receive

        _log.debug('创建连接到 %s 的 websocket', gateway)

        # poll event for OP Hello
        await ws.poll_event()

        if not resume:
            await ws.identify()
            return ws

        await ws.resume()
        return ws

    def wait_for(self, event, predicate, result=None):
        """等待满足检查函数的 DISPATCH 事件。

        Parameters
        -----------
        event: :class:`str`
            等待的事件名称全部大写。
        predicate
            使用数据参数来检查事件属性的函数。 data 参数是 JSON 消息中的“d”键。
        result
            一个采用相同数据参数并执行以将结果发送给未来的函数。如果为 ``None`` ，则返回数据。

        Returns
        --------
        asyncio.Future
            等待的 Future。
        """

        future = self.loop.create_future()
        entry = EventListener(event=event, predicate=predicate, result=result, future=future)
        self._dispatch_listeners.append(entry)
        return future

    async def identify(self):
        """发送 IDENTIFY 数据包。"""
        payload = {
            'op': self.IDENTIFY,
            'd': {
                'token': 'Bot ' + self.token,
                'properties': {
                    '$os': sys.platform,
                    '$browser': 'qq.py',
                    '$device': 'qq.py',
                },
            }
        }

        if self.shard_id is not None and self.shard_count is not None:
            payload['d']['shard'] = [self.shard_id, self.shard_count]

        state = self._connection
        if state._intents is not None:
            payload['d']['intents'] = state._intents.value

        await self.call_hooks('before_identify', self.shard_id, initial=self._initial_identify)
        await self.send_as_json(payload)
        _log.info('分片 ID %s 已发送 IDENTIFY 负载。', self.shard_id)

    async def resume(self):
        """发送 RESUME 数据包。"""
        payload = {
            'op': self.RESUME,
            'd': {
                'seq': self.sequence,
                'session_id': self.session_id,
                'token': 'Bot ' + self.token
            }
        }

        await self.send_as_json(payload)
        _log.info('分片 ID %s 已发送 RESUME 负载。', self.shard_id)

    async def received_message(self, msg, /):
        if type(msg) is bytes:
            self._buffer.extend(msg)

            if len(msg) < 4 or msg[-4:] != b'\x00\x00\xff\xff':
                return
            msg = self._zlib.decompress(self._buffer)
            msg = msg.decode('utf-8')
            self._buffer = bytearray()

        self.log_receive(msg)
        msg = utils._from_json(msg)

        _log.debug('分片 ID %s：WebSocket 事件：%s', self.shard_id, msg)
        event = msg.get('t')
        if event:
            self._dispatch('socket_event_type', event)

        op = msg.get('op')
        data = msg.get('d')
        seq = msg.get('s')
        if seq is not None:
            self.sequence = seq

        if self._keep_alive:
            self._keep_alive.tick()

        if op != self.DISPATCH:
            if op == self.RECONNECT:
                # "reconnect" can only be handled by the Client
                # so we terminate our connection and raise an
                # internal exception signalling to reconnect.
                _log.debug('收到 RECONNECT 操作码。')
                await self.close()
                raise ReconnectWebSocket(self.shard_id)

            if op == self.HEARTBEAT_ACK:
                if self._keep_alive:
                    self._keep_alive.ack()
                return

            if op == self.HEARTBEAT:
                if self._keep_alive:
                    beat = self._keep_alive.get_payload()
                    await self.send_as_json(beat)
                return

            if op == self.HELLO:
                interval = data['heartbeat_interval'] / 1000.0
                self._keep_alive = KeepAliveHandler(ws=self, interval=interval, shard_id=self.shard_id)
                # send a heartbeat immediately
                self._keep_alive.start()
                return

            if op == self.INVALIDATE_SESSION:
                if data is True:
                    await self.close()
                    raise ReconnectWebSocket(self.shard_id)

                self.sequence = None
                self.session_id = None
                _log.info('分片 ID %s 会话已失效。', self.shard_id)
                await self.close(code=1000)
                raise ReconnectWebSocket(self.shard_id, resume=False)

            _log.warning('未知 OP 代码 %s.', op)
            return

        if event == 'READY':
            self._trace = trace = data.get('_trace', [])
            self.sequence = msg['s']
            self.session_id = data['session_id']
            # pass back shard ID to ready handler
            data['__shard_id__'] = self.shard_id
            _log.info('分片 ID %s 已连接到 websocket ：%s（会话 ID：%s）。',
                      self.shard_id, ', '.join(trace), self.session_id)

        elif event == 'RESUMED':
            if not data:
                data = {}
            self._trace = trace = data.get('_trace', [])
            # pass back the shard ID to the resumed handler
            data['__shard_id__'] = self.shard_id
            _log.info('分片 ID %s 已在跟踪 %s 下成功恢复会话 %s。',
                      self.shard_id, self.session_id, ', '.join(trace))

        try:
            func = self._qq_parsers[event]
        except KeyError:
            _log.debug('未知事件 %s.', event)
        else:
            if event == 'READY':
                await func(data)
            else:
                func(data)

        # remove the dispatched listeners
        removed = []
        for index, entry in enumerate(self._dispatch_listeners):
            if entry.event != event:
                continue

            future = entry.future
            if future.cancelled():
                removed.append(index)
                continue

            try:
                valid = entry.predicate(data)
            except Exception as exc:
                future.set_exception(exc)
                removed.append(index)
            else:
                if valid:
                    ret = data if entry.result is None else entry.result(data)
                    future.set_result(ret)
                    removed.append(index)

        for index in reversed(removed):
            del self._dispatch_listeners[index]

    @property
    def latency(self):
        """:class:`float`: 以秒为单位测量 HEARTBEAT 和 HEARTBEAT_ACK 之间的延迟。"""
        heartbeat = self._keep_alive
        return float('inf') if heartbeat is None else heartbeat.latency

    def _can_handle_close(self):
        code = self._close_code or self.socket.close_code
        return code not in (1000, 4004, 4010, 4011, 4012, 4013, 4014, 4801)

    async def poll_event(self):
        """轮询 DISPATCH 事件并处理一般 websocket 循环。\

        Raises
        ------
        ConnectionClosed
            由于未处理的原因，websocket 连接被终止。
        """
        try:
            msg = await self.socket.receive(timeout=self._max_heartbeat_timeout)
            if msg.type is aiohttp.WSMsgType.TEXT:
                await self.received_message(msg.data)
            elif msg.type is aiohttp.WSMsgType.BINARY:
                await self.received_message(msg.data)
            elif msg.type is aiohttp.WSMsgType.ERROR:
                _log.debug('收到 %s', msg)
                raise msg.data
            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING, aiohttp.WSMsgType.CLOSE):
                _log.debug('收到 %s', msg)
                raise WebSocketClosure
        except (asyncio.TimeoutError, WebSocketClosure) as e:
            # Ensure the keep alive handler is closed
            if self._keep_alive:
                self._keep_alive.stop()
                self._keep_alive = None

            if isinstance(e, asyncio.TimeoutError):
                _log.info('接收数据包超时。正在尝试重新连接。')
                raise ReconnectWebSocket(self.shard_id) from None

            code = self._close_code or self.socket.close_code
            if self._can_handle_close():
                _log.info('Websocket 以 %s 关闭，正在尝试重新连接。', code)
                raise ReconnectWebSocket(self.shard_id) from None
            else:
                _log.info('Websocket 以 %s 关闭，无法重新连接。', code)
                raise ConnectionClosed(self.socket, shard_id=self.shard_id, code=code) from None

    async def debug_send(self, data, /):
        await self._rate_limiter.block()
        self._dispatch('socket_raw_send', data)
        await self.socket.send_str(data)

    async def send(self, data, /):
        await self._rate_limiter.block()
        await self.socket.send_str(data)

    async def send_as_json(self, data):
        try:
            await self.send(utils._to_json(data))
        except RuntimeError as exc:
            if not self._can_handle_close():
                raise ConnectionClosed(self.socket, shard_id=self.shard_id) from exc

    async def send_heartbeat(self, data):
        # This bypasses the rate limit handling code since it has a higher priority
        try:
            await self.socket.send_str(utils._to_json(data))
        except RuntimeError as exc:
            if not self._can_handle_close():
                raise ConnectionClosed(self.socket, shard_id=self.shard_id) from exc

    async def request_chunks(self, guild_id, query=None, *, limit, user_ids=None, presences=False, nonce=None):
        payload = {
            'op': self.REQUEST_MEMBERS,
            'd': {
                'guild_id': guild_id,
                'presences': presences,
                'limit': limit
            }
        }

        if nonce:
            payload['d']['nonce'] = nonce

        if user_ids:
            payload['d']['user_ids'] = user_ids

        if query is not None:
            payload['d']['query'] = query

        await self.send_as_json(payload)

    async def close(self, code=4000):
        if self._keep_alive:
            self._keep_alive.stop()
            self._keep_alive = None

        self._close_code = code
        await self.socket.close(code=code)
