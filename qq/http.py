from __future__ import annotations

import asyncio
import logging
import sys
import weakref
from types import TracebackType
from typing import ClassVar, Any, Optional, Sequence, Iterable, Dict, Union, TypeVar, Type, Coroutine, List, Tuple
from urllib.parse import quote as _uriquote
import aiohttp
import requests

from . import __version__, utils, role
from .error import HTTPException, Forbidden, NotFound, QQServerError, LoginFailure, GatewayNotFound
from .gateway import QQClientWebSocketResponse
from .message import Message
from .types import user, guild
from .utils import MISSING
from .types.channel import Channel as ChannelPayload
from .types.role import Role as RolePayload

T = TypeVar('T')
BE = TypeVar('BE', bound=BaseException)
MU = TypeVar('MU', bound='MaybeUnlock')
Response = Coroutine[Any, Any, T]
_log = logging.getLogger(__name__)

__all__ = ('Route', 'HTTPClient')


class Route:
    BASE: ClassVar[str] = 'https://api.sgroup.qq.com'

    def __init__(self, method: str, path: str, **parameters: Any) -> None:
        self.path: str = path
        self.method: str = method
        url = self.BASE + self.path
        if parameters:
            url = url.format_map({k: _uriquote(v) if isinstance(v, str) else v for k, v in parameters.items()})
        self.url: str = url

        # major parameters:
        self.channel_id: Optional[str] = parameters.get('channel_id')
        self.guild_id: Optional[str] = parameters.get('guild_id')
        self.token: Optional[str] = parameters.get('token')

    @property
    def bucket(self) -> str:
        # the bucket is just method + path w/ major parameters
        return f'{self.channel_id}:{self.guild_id}:{self.path}'


async def json_or_text(response: aiohttp.ClientResponse) -> Union[Dict[str, Any], str]:
    text = await response.text(encoding='utf-8')
    try:
        if response.headers['content-type'] == 'application/json':
            return utils._from_json(text)
    except KeyError:
        # Thanks Cloudflare
        pass

    return text


class MaybeUnlock:
    def __init__(self, lock: asyncio.Lock) -> None:
        self.lock: asyncio.Lock = lock
        self._unlock: bool = True

    def __enter__(self: MU) -> MU:
        return self

    def defer(self) -> None:
        self._unlock = False

    def __exit__(
            self,
            exc_type: Optional[Type[BE]],
            exc: Optional[BE],
            traceback: Optional[TracebackType],
    ) -> None:
        if self._unlock:
            self.lock.release()


class HTTPClient:
    """Represents an HTTP client sending HTTP requests to the Discord API."""

    def __init__(
            self,
            connector: Optional[aiohttp.BaseConnector] = None,
            *,
            proxy: Optional[str] = None,
            proxy_auth: Optional[aiohttp.BasicAuth] = None,
            loop: Optional[asyncio.AbstractEventLoop] = None,
            unsync_clock: bool = True,
    ) -> None:
        self._locks: weakref.WeakValueDictionary = weakref.WeakValueDictionary()
        user_agent = 'QQ Bot (https://github.com/foxwhite25/qq.py {0}) Python/{1[0]}.{1[1]} aiohttp/{2}'
        self.user_agent: str = user_agent.format(__version__, sys.version_info, aiohttp.__version__)
        self.token: Optional[str] = None
        self.proxy: Optional[str] = proxy
        self.proxy_auth: Optional[aiohttp.BasicAuth] = proxy_auth
        self._global_over: asyncio.Event = asyncio.Event()
        self._global_over.set()
        self.__session: aiohttp.ClientSession = MISSING
        self.connector = connector

    async def request(
            self,
            route: Route,
            *,
            # files: Optional[Sequence[File]] = None,
            form: Optional[Iterable[Dict[str, Any]]] = None,
            **kwargs: Any,
    ) -> Any:
        bucket = route.bucket
        method = route.method
        url = route.url

        lock = self._locks.get(bucket)
        if lock is None:
            lock = asyncio.Lock()
            if bucket is not None:
                self._locks[bucket] = lock

        headers: Dict[str, str] = {
            'User-Agent': self.user_agent,
        }

        # Add token to header
        if self.token is not None:
            headers['Authorization'] = 'Bot ' + self.token

        # Checking if it's a JSON request
        if 'json' in kwargs:
            headers['Content-Type'] = 'application/json'
            kwargs['data'] = utils._to_json(kwargs.pop('json'))

        kwargs['headers'] = headers

        # Proxy support
        if self.proxy is not None:
            kwargs['proxy'] = self.proxy
        if self.proxy_auth is not None:
            kwargs['proxy_auth'] = self.proxy_auth

        if not self._global_over.is_set():
            # wait until the global lock is complete
            await self._global_over.wait()

        response: Optional[aiohttp.ClientResponse] = None
        data: Optional[Union[Dict[str, Any], str]] = None
        await lock.acquire()
        with MaybeUnlock(lock) as maybe_lock:
            for tries in range(5):

                if form:
                    form_data = aiohttp.FormData()
                    for params in form:
                        form_data.add_field(**params)
                    kwargs['data'] = form_data
                try:
                    async with self.__session.request(method, url, **kwargs) as response:
                        _log.debug('%s %s with %s has returned %s', method, url, kwargs.get('data'), response.status)

                        # even errors have text involved in them so this is safe to call
                        data = await json_or_text(response)

                        # the request was successful so just return the text/json
                        if 300 > response.status >= 200:
                            _log.debug('%s %s has received %s', method, url, data)
                            return data

                        # we've received a 500, 502, or 504, unconditional retry
                        if response.status in {500, 502, 504}:
                            await asyncio.sleep(1 + tries * 2)
                            continue

                        # the usual error cases
                        if response.status == 403:
                            raise Forbidden(response, data)
                        elif response.status == 404:
                            raise NotFound(response, data)
                        elif response.status >= 500:
                            raise QQServerError(response, data)
                        else:
                            raise HTTPException(response, data)

                    # This is handling exceptions from the request
                except OSError as e:
                    # Connection reset by peer
                    if tries < 4 and e.errno in (54, 10054):
                        await asyncio.sleep(1 + tries * 2)
                        continue
                    raise

                if response is not None:
                    # We've run out of retries, raise.
                    if response.status >= 500:
                        raise QQServerError(response, data)

                    raise HTTPException(response, data)

                raise RuntimeError('Unreachable code in HTTP handling')

    async def static_login(self, token: str) -> user.User:
        # Necessary to get aiohttp to stop complaining about session creation
        self.__session = aiohttp.ClientSession(connector=self.connector, ws_response_class=QQClientWebSocketResponse)
        old_token = self.token
        self.token = token

        try:
            data = await self.request(Route('GET', '/users/@me'))
        except HTTPException as exc:
            self.token = old_token
            if exc.status == 401:
                raise LoginFailure('Improper token has been passed.') from exc
            raise

        return data

    def get_guilds(
            self,
            limit: int = 100,
            before: Optional[str] = None,
            after: Optional[str] = None,
    ) -> Response[List[guild.Guild]]:
        params: Dict[str, Any] = {
            'limit': limit,
        }

        if before:
            params['before'] = before
        if after:
            params['after'] = after

        return self.request(Route('GET', '/users/@me/guilds'), params=params)

    def _sync_get_guilds(self):
        headers: Dict[str, str] = {
            'User-Agent': self.user_agent,
        }
        if self.token is not None:
            headers['Authorization'] = 'Bot ' + self.token
        rsp = requests.get(f'https://api.sgroup.qq.com/users/@me/guilds', headers=headers)
        return rsp.json()

    def sync_guild_channels_roles(self, guild_id: int) -> Tuple[List[ChannelPayload], List[RolePayload]]:
        headers: Dict[str, str] = {
            'User-Agent': self.user_agent,
        }
        if self.token is not None:
            headers['Authorization'] = 'Bot ' + self.token
        rsp = requests.get(f'https://api.sgroup.qq.com/guilds/{guild_id}/channels', headers=headers)
        rsp2 = requests.get(f'https://api.sgroup.qq.com/guilds/{guild_id}/roles', headers=headers)
        return rsp.json(), rsp2.json()['roles']

    def get_guild(self, guild_id: int) -> Response[guild.Guild]:
        return self.request(Route('GET', '/guilds/{guild_id}', guild_id=guild_id))

    def get_guild_channels(self, guild_id: int) -> Response[guild.Guild]:
        return self.request(Route('GET', '/guilds/{guild_id}/channels', guild_id=guild_id))

    def get_message(self, channel_id: int, message_id: int) -> Response[Message]:
        r = Route('GET', '/channels/{channel_id}/messages/{message_id}', channel_id=channel_id, message_id=message_id)
        return self.request(r)

    # 身份组管理

    def get_roles(self, guild_id: int) -> Response[List[role.Role]]:
        return self.request(Route('GET', '/guilds/{guild_id}/roles', guild_id=guild_id))

    def edit_role(
            self, guild_id: int, role_id: int, *, reason: Optional[str] = None, **fields: Any
    ) -> Response[role.Role]:
        r = Route('PATCH', '/guilds/{guild_id}/roles/{role_id}', guild_id=guild_id, role_id=role_id)
        valid_keys = ('name', 'color', 'hoist')
        payload = {"info": {k: v for k, v in fields.items() if k in valid_keys}}
        return self.request(r, json=payload, reason=reason)

    def delete_role(self, guild_id: int, role_id: int, *, reason: Optional[str] = None) -> Response[None]:
        r = Route('DELETE', '/guilds/{guild_id}/roles/{role_id}', guild_id=guild_id, role_id=role_id)
        return self.request(r, reason=reason)

    def create_role(self, guild_id: int, *, reason: Optional[str] = None, **fields: Any) -> Response[role.Role]:
        r = Route('POST', '/guilds/{guild_id}/roles', guild_id=guild_id)
        return self.request(r, json=fields, reason=reason)

    def add_role(
            self, guild_id: int, user_id: int, role_id: int, *, reason: Optional[str] = None
    ) -> Response[None]:
        r = Route(
            'PUT',
            '/guilds/{guild_id}/members/{user_id}/roles/{role_id}',
            guild_id=guild_id,
            user_id=user_id,
            role_id=role_id,
        )
        return self.request(r, reason=reason)

    def remove_role(
            self, guild_id: str, user_id: str, role_id: str, *, reason: Optional[str] = None
    ) -> Response[None]:
        r = Route(
            'DELETE',
            '/guilds/{guild_id}/members/{user_id}/roles/{role_id}',
            guild_id=guild_id,
            user_id=user_id,
            role_id=role_id,
        )
        return self.request(r, reason=reason)

    async def get_from_cdn(self, url: str) -> bytes:
        async with self.__session.get(url) as resp:
            if resp.status == 200:
                return await resp.read()
            elif resp.status == 404:
                raise NotFound(resp, 'asset not found')
            elif resp.status == 403:
                raise Forbidden(resp, 'cannot retrieve asset')
            else:
                raise HTTPException(resp, 'failed to get asset')

    async def get_gateway(self, *, encoding: str = 'json', zlib: bool = True) -> str:
        try:
            data = await self.request(Route('GET', '/gateway'))
        except HTTPException as exc:
            raise GatewayNotFound() from exc
        return data['url']

    async def get_bot_gateway(self, *, encoding: str = 'json', zlib: bool = True) -> Tuple[int, str]:
        try:
            data = await self.request(Route('GET', '/gateway/bot'))
        except HTTPException as exc:
            raise GatewayNotFound() from exc

        if zlib:
            value = '{0}?encoding={1}&v=9&compress=zlib-stream'
        else:
            value = '{0}?encoding={1}&v=9'
        return data['shards'], value.format(data['url'], encoding)

    def recreate(self) -> None:
        if self.__session.closed:
            self.__session = aiohttp.ClientSession(
                connector=self.connector, ws_response_class=QQClientWebSocketResponse
            )

    async def close(self) -> None:
        if self.__session:
            await self.__session.close()

    async def ws_connect(self, url: str, *, compress: int = 0) -> Any:
        kwargs = {
            'proxy_auth': self.proxy_auth,
            'proxy': self.proxy,
            'max_msg_size': 0,
            'timeout': 30.0,
            'autoclose': False,
            'headers': {
                'User-Agent': self.user_agent,
            },
            'compress': compress,
        }

        return await self.__session.ws_connect(url, **kwargs)

