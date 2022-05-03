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
import logging
import sys
import weakref
from types import TracebackType
from typing import ClassVar, Any, Optional, Iterable, Dict, Union, TypeVar, Type, Coroutine, List, Tuple
from urllib.parse import quote as _uriquote

import aiohttp

from . import __version__, utils
from .embeds import Ark, Embed
from .error import HTTPException, Forbidden, NotFound, QQServerError, LoginFailure, GatewayNotFound
from .gateway import QQClientWebSocketResponse
from .types import user, guild, message, channel, member
from .types.embed import Ark as ArkPayload, Embed as EmbedPayload
from .types.message import Message
from .types.permission import (
    Permission as PermissionPayload,
    PermissionDemand as PermissionDemandPayload
)
from .types.role import (
    WrappedRole as WrappedRolePayload,
    Role as RolePayload
)
from .types.schedule import Schedule as SchedulePayload
from .utils import MISSING

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
    except Exception:
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
    """Represents an HTTP client sending HTTP requests to the QQ API."""

    def __init__(
            self,
            connector: Optional[aiohttp.BaseConnector] = None,
            *,
            proxy: Optional[str] = None,
            proxy_auth: Optional[aiohttp.BasicAuth] = None,
            loop: Optional[asyncio.AbstractEventLoop] = None,
            unsync_clock: bool = True,
    ) -> None:
        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop() if loop is None else loop
        self.connector = connector
        self.__session: aiohttp.ClientSession = MISSING  # filled in static_login
        self._locks: weakref.WeakValueDictionary = weakref.WeakValueDictionary()
        self._global_over: asyncio.Event = asyncio.Event()
        self._global_over.set()
        self.token: Optional[str] = None
        self.bot_token: bool = False
        self.proxy: Optional[str] = proxy
        self.proxy_auth: Optional[aiohttp.BasicAuth] = proxy_auth
        self.use_clock: bool = not unsync_clock

        user_agent = "QQBot (https://github.com/foxwhite25/qq.py {0}) Python/{1[0]}.{1[1]} aiohttp/{2}"
        self.user_agent: str = user_agent.format(__version__, sys.version_info, aiohttp.__version__)

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

        try:
            reason = kwargs.pop('reason')
        except KeyError:
            pass
        else:
            if reason:
                headers['X-Audit-Log-Reason'] = _uriquote(reason, safe='/ ')

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
                        _log.debug('%s %s 与 %s 已返回 %s Trace ID: %s', method, url, kwargs.get('data'),
                                   response.status, response.headers['X-Tps-trace-ID'])

                        # even errors have text involved in them so this is safe to call
                        data = await json_or_text(response)

                        # the request was successful so just return the text/json
                        if 300 > response.status >= 200:
                            if response.status != 204:
                                _log.debug('%s %s 已收到 %s', method, url, data)
                            return data

                        # we've received a 500, 502, or 504, unconditional retry
                        if response.status in (500, 502, 504):
                            await asyncio.sleep(1 + tries * 2)
                            continue

                        # the usual error cases
                        if response.status in [403, 401]:
                            raise Forbidden(response, data, route=route)
                        elif response.status == 404:
                            raise NotFound(response, data, route=route)
                        elif response.status >= 500:
                            raise QQServerError(response, data, route=route)
                        else:
                            raise HTTPException(response, data, route=route)

                    # This is handling exceptions from the request
                except OSError as e:
                    # Connection reset by peer
                    if tries < 4 and e.errno in (54, 10054):
                        await asyncio.sleep(1 + tries * 2)
                        continue
                    raise
                except QQServerError as e:
                    if tries < 4 and e.code in (620006,):
                        await asyncio.sleep(1 + tries * 2)
                        continue
                    raise e

                if response is not None:
                    # We've run out of retries, raise.
                    if response.status >= 500:
                        raise QQServerError(response, data)

                    raise HTTPException(response, data)

                raise RuntimeError('HTTP 处理中无法访问的代码')

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
                raise LoginFailure('传递了不正确的令牌。') from exc
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

    def get_guild(self, guild_id: int) -> Response[guild.Guild]:
        return self.request(Route('GET', '/guilds/{guild_id}', guild_id=guild_id))

    def get_guild_channels(self, guild_id: int) -> Response[guild.Guild]:
        return self.request(Route('GET', '/guilds/{guild_id}/channels', guild_id=guild_id))

    def get_message(self, channel_id: int, message_id: int) -> Response[Message]:
        r = Route('GET', '/channels/{channel_id}/messages/{message_id}', channel_id=channel_id, message_id=message_id)
        return self.request(r)

    # 身份组管理

    def get_roles(self, guild_id: int) -> Response[List[RolePayload]]:
        return self.request(Route('GET', '/guilds/{guild_id}/roles', guild_id=guild_id))

    def edit_role(
            self, guild_id: int, role_id: int, *, reason: Optional[str] = None, **fields: Any
    ) -> Response[RolePayload]:
        r = Route('PATCH', '/guilds/{guild_id}/roles/{role_id}', guild_id=guild_id, role_id=role_id)
        valid_keys = ('name', 'color', 'hoist')
        payload = {"info": {k: v for k, v in fields.items() if k in valid_keys}}
        return self.request(r, json=payload, reason=reason)

    def delete_role(self, guild_id: int, role_id: int, *, reason: Optional[str] = None) -> Response[None]:
        r = Route('DELETE', '/guilds/{guild_id}/roles/{role_id}', guild_id=guild_id, role_id=role_id)
        return self.request(r, reason=reason)

    def create_role(self, guild_id: int, *, reason: Optional[str] = None, **fields: Any) -> Response[
        WrappedRolePayload]:
        r = Route('POST', '/guilds/{guild_id}/roles', guild_id=guild_id)
        return self.request(r, json=fields, reason=reason)

    def add_role(
            self, guild_id: int, user_id: int, role_id: int, channel_id: Optional[int], *, reason: Optional[str] = None
    ) -> Response[None]:
        r = Route(
            'PUT',
            '/guilds/{guild_id}/members/{user_id}/roles/{role_id}',
            guild_id=guild_id,
            user_id=user_id,
            role_id=role_id,
        )
        if channel_id:
            payload = {'channel': {'id': str(channel_id)}}
            return self.request(r, json=payload, reason=reason)
        return self.request(r, reason=reason)

    def remove_role(
            self, guild_id: int, user_id: int, role_id: int, channel_id: Optional[int], *, reason: Optional[str] = None
    ) -> Response[None]:
        r = Route(
            'DELETE',
            '/guilds/{guild_id}/members/{user_id}/roles/{role_id}',
            guild_id=guild_id,
            user_id=user_id,
            role_id=role_id,
        )
        if channel_id:
            payload = {'channel': {'id': str(channel_id)}}
            return self.request(r, json=payload, reason=reason)
        return self.request(r, reason=reason)

    def create_channel(
            self,
            guild_id: int,
            channel_type: channel.ChannelType,
            *,
            reason: Optional[str] = None,
            **options: Any,
    ) -> Response[channel.GuildChannel]:
        payload = {
            'type': channel_type,
        }

        valid_keys = (
            'name',
            'parent_id',
            'position',
        )
        payload.update({k: str(v) for k, v in options.items() if k in valid_keys and v is not None})

        return self.request(Route('POST', '/guilds/{guild_id}/channels', guild_id=guild_id), json=payload,
                            reason=reason)

    def edit_channel(
            self,
            channel_id: int,
            *,
            reason: Optional[str] = None,
            **options: Any,
    ) -> Response[channel.Channel]:
        r = Route('PATCH', '/channels/{channel_id}', channel_id=channel_id)
        valid_keys = (
            'name',
            'parent_id',
            'position',
            'type',
        )
        payload = {k: v for k, v in options.items() if k in valid_keys}
        return self.request(r, reason=reason, json=payload)

    def bulk_channel_update(
            self,
            guild_id: int,
            datas: List[guild.ChannelPositionUpdate],
            *,
            reason: Optional[str] = None,
    ) -> List[Response[None]]:
        rsp = []
        for data in datas:
            valid_keys = (
                'name',
                'parent_id',
                'position',
                'type',
            )
            payload = {k: v for k, v in data.items() if k in valid_keys}
            r = Route('PATCH', '/channels/{channel_id}', channel_id=data.get('id'))
            rsp.append(self.request(r, reason=reason, json=payload))
        return rsp

    def delete_channel(
            self,
            channel_id: int,
            *,
            reason: Optional[str] = None,
    ) -> Response[None]:
        return self.request(Route('DELETE', '/channels/{channel_id}', channel_id=channel_id), reason=reason)

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

    def start_private_message(self, user_id: int, guild_id: int) -> Response[channel.DMChannel]:
        payload = {
            'recipient_id': str(user_id),
            'source_guild_id': str(guild_id),
        }

        return self.request(Route('POST', '/users/@me/dms'), json=payload)

    def send_message(
            self,
            channel_id: int,
            content: Optional[str],
            image_url: Optional[str],
            ark: Optional[Union[Ark, ArkPayload]],
            embed: Optional[Union[Embed, EmbedPayload]],
            *,
            tts: bool = False,
            message_id: str,
            message_reference: Optional[message.MessageReference] = None,
            direct=False
    ) -> Response[message.Message]:
        r = Route('POST', '/channels/{channel_id}/messages', channel_id=channel_id) if not direct else \
            Route('POST', '/dms/{guild_id}/messages', guild_id=channel_id)
        payload = {}

        if message_reference:
            payload['message_reference'] = message_reference

        if content:
            payload['content'] = content.replace(".", "\ufeff.")

        if tts:
            payload['tts'] = True

        if message_id:
            payload['msg_id'] = message_id

        if image_url:
            payload['image'] = image_url

        if ark:
            if isinstance(ark, Ark):
                ark = ark.to_dict()
            payload['ark'] = ark

        if embed:
            if isinstance(embed, Embed):
                embed = embed.to_dict()
            payload['embed'] = embed

        return self.request(r, json=payload)

    def get_members(
            self, guild_id: int, limit: int, after: Optional[int] = None
    ) -> Response[List[member.MemberWithUser]]:
        params: Dict[str, Any] = {
            'limit': limit,
        }
        if after:
            params['after'] = after

        r = Route('GET', '/guilds/{guild_id}/members', guild_id=guild_id)
        return self.request(r, params=params)

    def get_member(self, guild_id: int, member_id: int) -> Response[member.MemberWithUser]:
        return self.request(
            Route('GET', '/guilds/{guild_id}/members/{member_id}', guild_id=guild_id, member_id=member_id))

    def get_channel(self, channel_id: int) -> Response[channel.Channel]:
        r = Route('GET', '/channels/{channel_id}', channel_id=channel_id)
        return self.request(r)

    def kick(self, user_id: int, guild_id: int, add_blacklist: bool, reason: Optional[str] = None) -> Response[None]:
        r = Route('DELETE', '/guilds/{guild_id}/members/{user_id}', guild_id=guild_id, user_id=user_id)
        payload: Dict[str, Any] = {
            'add_blacklist': add_blacklist,
        }
        if reason:
            # thanks aiohttp
            r.url = f'{r.url}?reason={_uriquote(reason)}'

        return self.request(r, json=payload)

    def create_schedule(
            self,
            channel_id: int,
            name: str,
            start_timestamp: Union[datetime.datetime, float],
            end_timestamp: Union[datetime.datetime, float],
            jump_channel_id: int,
            remind_type: str,
            description: Optional[str],
            reason: Optional[str] = None
    ) -> Response[SchedulePayload]:
        payload: Dict[str, Any] = {
            "schedule": {
                "name": name,
                "start_timestamp": str(int(start_timestamp * 1000)) if isinstance(start_timestamp, float)
                else str(int(start_timestamp.timestamp() * 1000)),
                "end_timestamp": str(int(end_timestamp * 1000)) if isinstance(end_timestamp, float)
                else str(int(end_timestamp.timestamp() * 1000)),
                "jump_channel_id": str(jump_channel_id),
                "remind_type": remind_type
            }
        }

        if description is not None:
            payload["schedule"]["description"] = description

        r = Route('POST', '/channels/{channel_id}/schedules', channel_id=channel_id)
        return self.request(r, json=payload, reason=reason)

    def remove_schedule(self, channel_id: int, schedule_id: int, reason: Optional[str] = None) -> Response[None]:
        r = Route(
            'DELEtE', '/channels/{channel_id}/schedules/{schedule_id}',
            channel_id=channel_id,
            schedule_id=schedule_id
        )

        return self.request(r, reason=reason)

    def mute_member(
            self, user_id: int, guild_id: int, duration: Union[datetime.datetime, int], reason: Optional[str] = None
    ) -> Response[None]:
        payload: Dict[str, Any] = {}
        if isinstance(duration, datetime.datetime):
            payload['mute_end_timestamp'] = str(int(duration.timestamp() * 1000))
        else:
            payload['mute_seconds'] = str(duration)

        r = Route('PATCH', '/guilds/{guild_id}/members/{user_id}/mute', guild_id=guild_id, user_id=user_id)
        return self.request(r, json=payload, reason=reason)

    def mute_members(
            self, user_id: List[int],
            guild_id: int,
            duration: Union[datetime.datetime, int],
            reason: Optional[str] = None
    ) -> Response[None]:
        payload: Dict[str, Any] = {'user_ids': user_id}

        if isinstance(duration, datetime.datetime):
            payload['mute_end_timestamp'] = str(int(duration.timestamp() * 1000))
        else:
            payload['mute_seconds'] = str(duration)

        r = Route('PATCH', '/guilds/{guild_id}/mute', guild_id=guild_id)
        return self.request(r, json=payload, reason=reason)

    def mute_guild(
            self, guild_id: int, duration: Union[datetime.datetime, int], reason: Optional[str] = None
    ) -> Response[None]:
        payload: Dict[str, Any] = {}
        if isinstance(duration, datetime.datetime):
            payload['mute_end_timestamp'] = str(int(duration.timestamp() * 1000))
        else:
            payload['mute_seconds'] = str(duration)

        r = Route('PATCH', '/guilds/{guild_id}/mute', guild_id=guild_id)
        return self.request(r, json=payload, reason=reason)

    def delete_message(
            self, channel_id: int, message_id: str, hidetip: bool, *, reason: Optional[str] = None,
    ) -> Response[None]:
        r = Route('DELETE', '/channels/{channel_id}/messages/{message_id}', channel_id=channel_id,
                  message_id=message_id)
        params = {'hidetip': 'true' if hidetip else 'false'}
        return self.request(r, reason=reason, params=params)

    def delete_messages(
            self, channel_id: int, message_ids: List[str], *, reason: Optional[str] = None
    ) -> Response[None]:
        r = Route('POST', '/channels/{channel_id}/messages/bulk-delete', channel_id=channel_id)
        payload = {
            'messages': message_ids,
        }
        return self.request(r, json=payload, reason=reason)

    def logs_from(
            self,
            channel_id: int,
            limit: int,
            before: Optional[datetime.datetime] = None,
            after: Optional[datetime.datetime] = None,
            around: Optional[datetime.datetime] = None,
    ) -> Response[List[message.Message]]:
        params: Dict[str, Any] = {
            'limit': limit,
        }

        if before is not None:
            params['before'] = datetime.datetime.timestamp(before)
        if after is not None:
            params['after'] = datetime.datetime.timestamp(after)
        if around is not None:
            params['around'] = datetime.datetime.timestamp(around)

        return self.request(Route('GET', '/channels/{channel_id}/messages', channel_id=channel_id), params=params)

    def get_permission(self, guild_id: int) -> Response[List[PermissionPayload]]:
        return self.request(Route('GET', '/guilds/{guild_id}/api_permission', guild_id=guild_id))

    def demand_permission(
            self,
            guild_id: int,
            channel_id: int,
            desc: str,
            path: str,
            method: str
    ) -> Response[PermissionDemandPayload]:

        payload: Dict[str, Any] = {
            "channel_id": str(channel_id),
            "api_identify": {"path": path, "method": method},
            "desc": desc
        }

        return self.request(Route('POST', '/guilds/{guild_id}/api_permission/demand', guild_id=guild_id), json=payload)

    def global_pin_message(
            self,
            guild_id: int,
            channel_id: Optional[int] = None,
            message_id: Optional[str] = None,
            announces_type: Optional[int] = None,
            recommend_channels: Optional[Dict[int, str]] = None,
            reason: Optional[str] = None
    ):
        r = Route(
            'POST',
            '/guilds/{guild_id}/announces',
            guild_id=guild_id,
        )
        if recommend_channels:
            recommend_channels: List[Dict[str, str]] = [
                {
                    'channel_id': str(m),
                    'introduce': n
                } for m, n in recommend_channels.items()
            ]
        payload: Dict[str, Any] = {}
        if channel_id is not None:
            payload['channel_id'] = channel_id
        if message_id is not None:
            payload['message_id'] = message_id
        if announces_type is not None:
            payload['announces_types'] = announces_type
        if recommend_channels is not None:
            payload['recommend_channels'] = recommend_channels
        return self.request(r, json=payload, reason=reason)

    def global_unpin_message(self, guild_id: int, message_id: str, reason: Optional[str] = None):
        r = Route(
            'DELETE',
            '/guilds/{guild_id}/announces/{message_id}',
            guild_id=guild_id,
            message_id=message_id
        )
        return self.request(r, reason=reason)

    def channel_pin_message(self, channel_id: int, message_id: str, reason: Optional[str] = None):
        r = Route(
            'POST',
            '/channels/{channel_id}/pins/{message_id}',
            channel_id=channel_id,
            message_id=message_id,
        )
        return self.request(r, reason=reason)

    def channel_unpin_message(self, channel_id: int, message_id: str, reason: Optional[str] = None):
        r = Route(
            'DELETE',
            '/channels/{channel_id}/pins/{message_id}',
            channel_id=channel_id,
            message_id=message_id
        )
        return self.request(r, reason=reason)

    def add_reaction(
            self, channel_id: int, message_id: str, custom: bool, id: int
    ) -> Response[None]:
        r = Route(
            'PUT',
            '/channels/{channel_id}/messages/{message_id}/reactions/{type}/{id}',
            channel_id=channel_id,
            message_id=message_id,
            type=1 if custom else 2,
            id=id
        )
        return self.request(r)

    def remove_reaction(
            self, channel_id: int, message_id: str, custom: bool, id: int
    ) -> Response[None]:
        r = Route(
            'DELETE',
            '/channels/{channel_id}/messages/{message_id}/reactions/{emoji}/{member_id}',
            channel_id=channel_id,
            message_id=message_id,
            type=1 if custom else 2,
            id=id
        )
        return self.request(r)

    def send_guide(
            self,
            channel_id: int,
            content: str,
    ):
        r = Route(
            'POST',
            '/channels/{channel_id}/settingguide',
            channel_id=channel_id
        )
        payload = {'content': content}
        return self.request(r, json=payload)
