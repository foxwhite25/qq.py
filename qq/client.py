__all__ = ('Client',)

import asyncio
import datetime
import logging
from typing import Optional, Any

import aiohttp

from .aiorequests import *
from .guild import Guild
from .http import HTTPClient
from .iterators import GuildIterator

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
        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop() if loop is None else loop
        self.token = f"{options.pop('app_id', None)}.{options.pop('token', None)}"

        connector: Optional[aiohttp.BaseConnector] = options.pop('connector', None)
        proxy: Optional[str] = options.pop('proxy', None)
        proxy_auth: Optional[aiohttp.BasicAuth] = options.pop('proxy_auth', None)
        unsync_clock: bool = options.pop('assume_unsync_clock', True)
        self.http: HTTPClient = HTTPClient(connector, proxy=proxy, proxy_auth=proxy_auth, unsync_clock=unsync_clock,
                                           loop=self.loop)

    async def get_guild(self, guild_id: str) -> Optional[Guild]:
        data = await self.http.get_guild(guild_id)
        channels = await self.http.get_guild_channels(guild_id)
        return Guild(data=data, channels=channels)

    async def get_guilds(
            self,
            *,
            limit: Optional[int] = 100,
            before: datetime.datetime = None,
            after: datetime.datetime = None
    ):
        return GuildIterator(self, limit=limit, before=before, after=after)

    def _cleanup_loop(loop: asyncio.AbstractEventLoop) -> None:
        _log.info('Closing the event loop.')
        loop.close()
