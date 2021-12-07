from __future__ import annotations

__all__ = ('Client',)

import asyncio
import datetime
import logging
import sys
import traceback
from typing import Optional, Any, Dict, Callable, List, Tuple, Coroutine

import aiohttp

from .state import ConnectionState
from .gateway import QQWebSocket
from .guild import Guild
from .http import HTTPClient
from .iterators import GuildIterator
from .user import ClientUser, User

URL = r'https://api.sgroup.qq.com'
_log = logging.getLogger(__name__)


def _cancel_tasks(loop: asyncio.AbstractEventLoop) -> None:
    tasks = {t for t in asyncio.all_tasks(loop=loop) if not t.done()}

    if not tasks:
        return

    _log.info('Cleaning up after %d tasks.', len(tasks))
    for task in tasks:
        task.cancel()

    loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
    _log.info('All tasks finished cancelling.')

    for task in tasks:
        if task.cancelled():
            continue
        if task.exception() is not None:
            loop.call_exception_handler({
                'message': 'Unhandled exception during Client.run shutdown.',
                'exception': task.exception(),
                'task': task
            })


def _cleanup_loop(loop: asyncio.AbstractEventLoop) -> None:
    try:
        _cancel_tasks(loop)
        loop.run_until_complete(loop.shutdown_asyncgens())
    finally:
        _log.info('Closing the event loop.')
        loop.close()


class Client:
    def __init__(
            self,
            *,
            loop: Optional[asyncio.AbstractEventLoop] = None,
            **options: Any,
    ):
        self.ws: QQWebSocket = None  # type: ignore
        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop() if loop is None else loop
        self._listeners: Dict[str, List[Tuple[asyncio.Future, Callable[..., bool]]]] = {}
        self.token = f"{options.pop('app_id', None)}.{options.pop('token', None)}"
        self.shard_id: Optional[int] = options.get('shard_id')
        self.shard_count: Optional[int] = options.get('shard_count')

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
        print(f'Ignoring exception in {event_method}', file=sys.stderr)
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
        _log.debug('Dispatching event %s', event)
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
        _log.info('logging in using static token')

        data = await self.http.static_login(token.strip())
        self._connection.user = ClientUser(state=self._connection, data=data)

    @property
    def user(self) -> Optional[ClientUser]:
        """Optional[:class:`.ClientUser`]: Represents the connected client. ``None`` if not logged in."""
        return self._connection.user

    @property
    def guilds(self) -> List[Guild]:
        """List[:class:`.Guild`]: The guilds that the connected client is a member of."""
        return self._connection.guilds

    def get_guild(self, id: int, /) -> Optional[Guild]:
        """Returns a guild with the given ID.
        Parameters
        -----------
        id: :class:`int`
            The ID to search for.
        Returns
        --------
        Optional[:class:`.Guild`]
            The guild or ``None`` if not found.
        """
        return self._connection._get_guild(id)

    def get_user(self, id: int, /) -> Optional[User]:
        """Returns a user with the given ID.
        Parameters
        -----------
        id: :class:`int`
            The ID to search for.
        Returns
        --------
        Optional[:class:`~discord.User`]
            The user or ``None`` if not found.
        """
        return self._connection.get_user(id)

    async def fetch_guild(self, guild_id: int) -> Optional[Guild]:
        data = await self.http.get_guild(guild_id)
        return Guild(data=data, state=self._connection)

    async def fetch_guilds(
            self,
            *,
            limit: Optional[int] = 100,
            before: datetime.datetime = None,
            after: datetime.datetime = None
    ):
        return GuildIterator(self, limit=limit, before=before, after=after)
