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
import concurrent.futures
import copy
import inspect
import itertools
import logging
import os
from collections import deque, OrderedDict
from typing import Callable, TYPE_CHECKING, Dict, Any, Optional, List, Union, Deque, Coroutine, TypeVar, Tuple

from . import utils
from .audio import AudioAction
from .channel import PartialMessageable, TextChannel, _channel_factory, DMChannel
from .flags import Intents
from .guild import Guild
from .member import Member
from .mention import AllowedMentions
from .message import Message, MessageAudit
from .object import Object
from .partial_emoji import PartialEmoji
from .raw_models import RawReactionActionEvent, RawReactionClearEvent, RawReactionClearEmojiEvent
from .user import User, ClientUser

if TYPE_CHECKING:
    from .message import MessageableChannel
    from .abc import PrivateChannel
    from .guild import GuildChannel
    from .http import HTTPClient
    from .client import Client
    from .gateway import QQWebSocket

    from .types.user import User as UserPayload
    from .types.message import Message as MessagePayload
    from .types.guild import Guild as GuildPayload
    from .types.channel import DMChannel as DMChannelPayload

    T = TypeVar('T')
    CS = TypeVar('CS', bound='ConnectionState')
    Channel = Union[GuildChannel, PartialMessageable]


class ChunkRequest:
    def __init__(
            self,
            guild_id: int,
            loop: asyncio.AbstractEventLoop,
            resolver: Callable[[int], Any],
            *,
            cache: bool = True,
    ) -> None:
        self.guild_id: int = guild_id
        self.resolver: Callable[[int], Any] = resolver
        self.loop: asyncio.AbstractEventLoop = loop
        self.cache: bool = cache
        self.nonce: str = os.urandom(16).hex()
        self.buffer: List[Member] = []
        self.waiters: List[asyncio.Future[List[Member]]] = []

    def add_members(self, members: List[Member]) -> None:
        self.buffer.extend(members)
        if self.cache:
            guild = self.resolver(self.guild_id)
            if guild is None:
                return

            for member in members:
                existing = guild.get_member(member.id)
                if existing is None or existing.joined_at is None:
                    guild._add_member(member)

    async def wait(self) -> List[Member]:
        future = self.loop.create_future()
        self.waiters.append(future)
        try:
            return await future
        finally:
            self.waiters.remove(future)

    def get_future(self) -> asyncio.Future[List[Member]]:
        future = self.loop.create_future()
        self.waiters.append(future)
        return future

    def done(self) -> None:
        for future in self.waiters:
            if not future.done():
                future.set_result(self.buffer)


_log = logging.getLogger(__name__)


async def logging_coroutine(coroutine: Coroutine[Any, Any, T], *, info: str) -> Optional[T]:
    try:
        await coroutine
    except Exception:
        _log.exception('%s 期间发生异常', info)


class ConnectionState:
    if TYPE_CHECKING:
        _get_websocket: Callable[..., QQWebSocket]
        _get_client: Callable[..., Client]
        _parsers: Dict[str, Callable[[Dict[str, Any]], None]]

    def __init__(
            self,
            *,
            dispatch: Callable,
            handlers: Dict[str, Callable],
            hooks: Dict[str, Callable],
            http: HTTPClient,
            loop: asyncio.AbstractEventLoop,
            **options: Any,
    ) -> None:
        self.loop: asyncio.AbstractEventLoop = loop
        self.http: HTTPClient = http
        self.max_messages: Optional[int] = options.get('max_messages', 1000)
        if self.max_messages is not None and self.max_messages <= 0:
            self.max_messages = 1000

        self.dispatch: Callable = dispatch
        self.handlers: Dict[str, Callable] = handlers
        self.hooks: Dict[str, Callable] = hooks
        self.shard_count: Optional[int] = None
        self._ready_task: Optional[asyncio.Task] = None
        self.application_id: Optional[int] = options.get('application_id')
        self.heartbeat_timeout: float = options.get('heartbeat_timeout', 60.0)
        self.guild_ready_timeout: float = options.get('guild_ready_timeout', 2.0)
        self.pool = concurrent.futures.ThreadPoolExecutor()
        if self.guild_ready_timeout < 0:
            raise ValueError('guild_ready_timeout 不能为负')

        allowed_mentions = options.get('allowed_mentions')

        if allowed_mentions is not None and not isinstance(allowed_mentions, AllowedMentions):
            raise TypeError('allowed_mentions 参数必须是 AllowedMentions')

        self.allowed_mentions: Optional[AllowedMentions] = allowed_mentions
        self._chunk_requests: Dict[Union[int, str], ChunkRequest] = {}

        intents = options.get('intents', None)
        if intents is not None:
            if not isinstance(intents, Intents):
                raise TypeError(f'Intents 参数必须是 Intents 而不是 {type(intents)!r}')
        else:
            intents = Intents.default()

        if not intents.guilds:
            _log.warning('频道 Intents 似乎被禁用。这可能会导致状态相关的问题。')

        self._chunk_guilds: bool = options.get('chunk_guilds_at_startup', intents.members)

        # Ensure these two are set properly
        if not intents.members and self._chunk_guilds:
            raise ValueError('Intents.members 必须在启动时启用分块频道。')

        self._intents: Intents = intents

        if not intents.members:
            self.store_user = self.create_user  # type: ignore
            self.deref_user = self.deref_user_no_intents  # type: ignore

        self.parsers = parsers = {}
        for attr, func in inspect.getmembers(self):
            if attr.startswith('parse_'):
                parsers[attr[6:].upper()] = func

        self.clear()

    def clear(self) -> None:
        self.user: Optional[ClientUser] = None
        self._users: Dict[int, User] = {}
        self._guilds: Dict[int, Guild] = {}

        # LRU of max size 128
        self._private_channels: OrderedDict[int, PrivateChannel] = OrderedDict()
        # extra dict to look up private channels by user id
        self._private_channels_by_user: Dict[int, DMChannel] = {}

        if self.max_messages is not None:
            self._messages: Optional[Deque[Message]] = deque(maxlen=self.max_messages)
        else:
            self._messages: Optional[Deque[Message]] = None

    def process_chunk_requests(self, guild_id: int, nonce: Optional[str], members: List[Member],
                               complete: bool) -> None:
        removed = []
        for key, request in self._chunk_requests.items():
            if request.guild_id == guild_id and request.nonce == nonce:
                request.add_members(members)
                if complete:
                    request.done()
                    removed.append(key)

        for key in removed:
            del self._chunk_requests[key]

    def call_handlers(self, key: str, *args: Any, **kwargs: Any) -> None:
        try:
            func = self.handlers[key]
        except KeyError:
            pass
        else:
            func(*args, **kwargs)

    async def call_hooks(self, key: str, *args: Any, **kwargs: Any) -> None:
        try:
            coro = self.hooks[key]
        except KeyError:
            pass
        else:
            await coro(*args, **kwargs)

    @property
    def self_id(self) -> Optional[int]:
        u = self.user
        return u.id if u else None

    @property
    def intents(self) -> Intents:
        ret = Intents.none()
        ret.value = self._intents.value
        return ret

    def store_user(self, data: UserPayload) -> User:
        user_id = int(data['id'])
        try:
            return self._users[user_id]
        except KeyError:
            user = User(state=self, data=data)
            self._users[user_id] = user
            user._stored = True
            return user

    def deref_user(self, user_id: int) -> None:
        self._users.pop(user_id, None)

    def create_user(self, data: UserPayload) -> User:
        return User(state=self, data=data)

    def deref_user_no_intents(self, user_id: int) -> None:
        return

    def get_user(self, id: Optional[int]) -> Optional[User]:
        # the keys of self._users are ints
        return self._users.get(id)  # type: ignore

    @property
    def guilds(self) -> List[Guild]:
        return list(self._guilds.values())

    def _get_guild(self, guild_id: Optional[int]) -> Optional[Guild]:
        # the keys of self._guilds are ints
        guild_id = int(guild_id)
        return self._guilds.get(guild_id)  # type: ignore

    def _add_guild(self, guild: Guild) -> None:
        self._guilds[guild.id] = guild

    def _remove_guild(self, guild: Guild) -> None:
        self._guilds.pop(guild.id, None)
        del guild

    def _get_message(self, msg_id: Optional[str]) -> Optional[Message]:
        return utils.find(lambda m: m.id == msg_id, reversed(self._messages)) if self._messages else None

    def _add_guild_from_data(self, data: GuildPayload) -> Guild:
        guild = Guild(data=data, state=self)
        self._add_guild(guild)
        return guild

    def _guild_needs_chunking(self, guild: Guild) -> bool:
        # If presences are enabled then we get back the old guild.large behaviour
        return False
        # return self._chunk_guilds and not guild.chunked and not guild.large

    def _get_guild_channel(self, data: MessagePayload) -> Tuple[Union[Channel], Optional[Guild]]:
        channel_id = int(data['channel_id'])
        if 'direct_message' not in data:
            guild = self._get_guild(int(data['guild_id']))
            channel = guild and guild._resolve_channel(channel_id)
        else:
            channel = DMChannel._from_message(state=self, channel_id=channel_id, guild_id=int(data['guild_id']))
            self._add_private_channel(channel)
            guild = None
        return channel or PartialMessageable(state=self, id=channel_id), guild

    def get_reaction_emoji(self, data) -> Union[PartialEmoji]:
        emoji_id = data.get('id')

        if not emoji_id:
            return data['name']

        return PartialEmoji.with_state(self, id=emoji_id, custom=False)

    async def chunker(
            self, guild_id: int, query: str = '', limit: int = 0, presences: bool = False, *,
            nonce: Optional[str] = None
    ) -> None:
        ws = self._get_websocket(guild_id)  # This is ignored upstream
        await ws.request_chunks(guild_id, query=query, limit=limit, presences=presences, nonce=nonce)

    async def query_members(self, guild: Guild, query: str, limit: int, user_ids: List[int], cache: bool,
                            presences: bool):
        guild_id = guild.id
        ws = self._get_websocket(guild_id)
        if ws is None:
            raise RuntimeError('不知何故没有这个 guild_id 的 websocket')

        request = ChunkRequest(guild.id, self.loop, self._get_guild, cache=cache)
        self._chunk_requests[request.nonce] = request

        try:
            # start the query operation
            await ws.request_chunks(
                guild_id, query=query, limit=limit, user_ids=user_ids, presences=presences, nonce=request.nonce
            )
            return await asyncio.wait_for(request.wait(), timeout=30.0)
        except asyncio.TimeoutError:
            _log.warning('等待查询 %r 的块超时，guild_id %d 限制为 %d', query, limit,
                         guild_id)
            raise

    @property
    def private_channels(self) -> List[PrivateChannel]:
        return list(self._private_channels.values())

    def _get_private_channel(self, channel_id: Optional[int]) -> Optional[PrivateChannel]:
        try:
            # the keys of self._private_channels are ints
            value = self._private_channels[channel_id]  # type: ignore
        except KeyError:
            return None
        else:
            self._private_channels.move_to_end(channel_id)  # type: ignore
            return value

    def _get_private_channel_by_user(self, user_id: Optional[int]) -> Optional[DMChannel]:
        # the keys of self._private_channels are ints
        return self._private_channels_by_user.get(user_id)  # type: ignore

    def _add_private_channel(self, channel: PrivateChannel) -> None:
        channel_id = channel.id
        self._private_channels[channel_id] = channel

        if len(self._private_channels) > 128:
            _, to_remove = self._private_channels.popitem(last=False)
            if isinstance(to_remove, DMChannel) and to_remove.recipient:
                self._private_channels_by_user.pop(to_remove.recipient.id, None)

        if isinstance(channel, DMChannel) and channel.recipient:
            self._private_channels_by_user[channel.recipient.id] = channel

    def add_dm_channel(self, data: DMChannelPayload, recipients) -> DMChannel:
        # self.user is *always* cached when this is called
        channel = DMChannel(me=self.user, state=self, data=data, recipients=recipients)  # type: ignore
        self._add_private_channel(channel)
        return channel

    def _remove_private_channel(self, channel: PrivateChannel) -> None:
        self._private_channels.pop(channel.id, None)
        if isinstance(channel, DMChannel):
            recipient = channel.recipient
            if recipient is not None:
                self._private_channels_by_user.pop(recipient.id, None)

    async def _delay_ready(self) -> None:
        try:
            states = []
            while True:
                # this snippet of code is basically waiting N seconds
                # until the last GUILD_CREATE was sent
                try:
                    guild = await asyncio.wait_for(self._ready_state.get(), timeout=self.guild_ready_timeout)
                except asyncio.TimeoutError:
                    break
                else:
                    if self._guild_needs_chunking(guild):
                        future = await self.chunk_guild(guild, wait=False)
                        states.append((guild, future))
                    else:
                        if guild.unavailable is False:
                            self.dispatch('guild_available', guild)
                        else:
                            self.dispatch('guild_join', guild)

            for guild, future in states:
                try:
                    await asyncio.wait_for(future, timeout=5.0)
                except asyncio.TimeoutError:
                    _log.warning('分片 ID %s 等待 guild_id %s 的块时超时。', guild.shard_id, guild.id)

                if guild.unavailable is False:
                    self.dispatch('guild_available', guild)
                else:
                    self.dispatch('guild_join', guild)

            # remove the state
            try:
                del self._ready_state
            except AttributeError:
                pass  # already been deleted somehow

        except asyncio.CancelledError:
            pass
        else:
            # dispatch the event
            self.call_handlers('ready')
            self.dispatch('ready')
        finally:
            self._ready_task = None

    async def parse_ready(self, data) -> None:
        if self._ready_task is not None:
            self._ready_task.cancel()

        self._ready_state = asyncio.Queue()
        self.clear()
        self.user = ClientUser(state=self, data=data['user'])
        self.store_user(data['user'])

        if self.application_id is None:
            try:
                application = data['application']
            except KeyError:
                pass
            else:
                self.application_id = application.get('id')

        result = await self.http.get_guilds()

        for guild_data in result:
            guild = self._add_guild_from_data(guild_data)
            await guild.fill_in()

        self.dispatch('connect')
        self._ready_task = asyncio.create_task(self._delay_ready())

    def parse_resumed(self, data) -> None:
        self.dispatch('resumed')

    def parse_at_message_create(self, data) -> None:
        channel, guild = self._get_guild_channel(data)
        direct = True if 'direct_message' in data else False
        # channel would be the correct type here
        message = Message(channel=channel, data=data, state=self, direct=direct)  # type: ignore
        self.dispatch('message', message)
        if self._messages is not None:
            self._messages.append(message)
        # we ensure that the channel is either a TextChannel or Thread
        if channel and channel.__class__ in (TextChannel,):
            channel.last_message_id = message.id  # type: ignore

    def parse_message_create(self, data) -> None:
        self.parse_at_message_create(data)

    def parse_direct_message_create(self, data) -> None:
        self.parse_at_message_create(data)

    def parse_message_audit_pass(self, data) -> None:
        self.dispatch('message_audit', MessageAudit(state=self, data=data, audit_state=True))

    def parse_message_audit_reject(self, data) -> None:
        self.dispatch('message_audit', MessageAudit(state=self, data=data, audit_state=False))

    def parse_channel_delete(self, data) -> None:
        guild = self._get_guild(data.get('guild_id'))
        channel_id = int(data['id'])
        if guild is not None:
            channel = guild.get_channel(channel_id)
            if channel is not None:
                guild._remove_channel(channel)
                self.dispatch('guild_channel_delete', channel)

    def parse_channel_update(self, data) -> None:
        channel_id = int(data['id'])
        guild_id = data.get('guild_id')
        if guild_id.isnumeric():
            guild_id = int(guild_id)
        guild = self._get_guild(guild_id)
        if guild is not None:
            channel = guild.get_channel(channel_id)
            if channel is not None:
                old_channel = copy.copy(channel)
                channel._update(guild, data)
                self.dispatch('guild_channel_update', old_channel, channel)
            else:
                _log.debug('CHANNEL_UPDATE 引用了一个未知的子频道 ID：%s。丢弃。', channel_id)
        else:
            _log.debug('CHANNEL_UPDATE 引用了一个未知的频道 ID：%s。 丢弃。', guild_id)

    def parse_channel_create(self, data) -> None:
        factory, ch_type = _channel_factory(data['type'])
        if factory is None:
            _log.debug('CHANNEL_CREATE 引用了未知的子频道类型 %s。丢弃。', data['type'])
            return

        guild_id = data.get('guild_id')
        guild = self._get_guild(guild_id)
        if guild is not None:
            # the factory can't be a DMChannel or GroupChannel here
            channel = factory(guild=guild, state=self, data=data)  # type: ignore
            guild._add_channel(channel)  # type: ignore
            self.dispatch('guild_channel_create', channel)
        else:
            _log.debug('CHANNEL_CREATE 引用了一个未知的频道 ID：%s。丢弃。', guild_id)
            return

    def parse_guild_member_add(self, data) -> None:
        guild = self._get_guild(int(data['guild_id']))
        if guild is None:
            _log.debug('GUILD_MEMBER_ADD 引用了一个未知的频道 ID：%s。丢弃。', data['guild_id'])
            return

        member = Member(guild=guild, data=data, state=self)
        guild._add_member(member)

        try:
            guild._member_count += 1
        except (AttributeError, TypeError):
            pass

        self.dispatch('member_join', member)

    def parse_guild_member_remove(self, data) -> None:
        guild = self._get_guild(int(data['guild_id']))
        if guild is not None:
            try:
                guild._member_count -= 1
            except (AttributeError, TypeError):
                pass

            user_id = int(data['user']['id'])
            member = guild.get_member(user_id)
            if member is not None:
                guild._remove_member(member)  # type: ignore
                self.dispatch('member_remove', member)
        else:
            _log.debug('GUILD_MEMBER_REMOVE 引用了一个未知的频道 ID：%s。丢弃。', data['guild_id'])

    def parse_guild_member_update(self, data) -> None:
        guild = self._get_guild(int(data['guild_id']))
        user = data['user']
        user_id = int(user['id'])
        if guild is None:
            _log.debug('GUILD_MEMBER_UPDATE 引用了一个未知的频道 ID：%s。丢弃。', data['guild_id'])
            return

        member = guild.get_member(user_id)
        if member is not None:
            old_member = Member._copy(member)
            member._update(data)
            user_update = member._update_inner_user(user)
            if user_update:
                self.dispatch('user_update', user_update[0], user_update[1])

            self.dispatch('member_update', old_member, member)
        else:
            member = Member(data=data, guild=guild, state=self)

            # Force an update on the inner user if necessary
            user_update = member._update_inner_user(user)
            if user_update:
                self.dispatch('user_update', user_update[0], user_update[1])

            guild._add_member(member)
            _log.debug('GUILD_MEMBER_UPDATE 引用了一个未知的成员 ID：%s。丢弃。', user_id)

    def _get_create_guild(self, data):
        return self._add_guild_from_data(data)

    def is_guild_evicted(self, guild) -> bool:
        return guild.id not in self._guilds

    async def chunk_guild(self, guild, *, wait=True, cache=None):
        cache = cache
        request = self._chunk_requests.get(guild.id)
        if request is None:
            self._chunk_requests[guild.id] = request = ChunkRequest(guild.id, self.loop, self._get_guild, cache=cache)
            await self.chunker(guild.id, nonce=request.nonce)

        if wait:
            return await request.wait()
        return request.get_future()

    async def _chunk_and_dispatch(self, guild, unavailable):
        try:
            await asyncio.wait_for(self.chunk_guild(guild), timeout=60.0)
        except asyncio.TimeoutError:
            _log.info('不知何故 chunk 超时了')

        if unavailable is False:
            self.dispatch('guild_available', guild)
        else:
            self.dispatch('guild_join', guild)

    def parse_guild_create(self, data) -> None:
        unavailable = data.get('unavailable')
        if unavailable is True:
            # joined a guild with unavailable == True so..
            return

        guild = self._get_create_guild(data)

        try:
            # Notify the on_ready state, if any, that this guild is complete.
            self._ready_state.put_nowait(guild)
        except AttributeError:
            pass
        else:
            # If we're waiting for the event, put the rest on hold
            return

        # check if it requires chunking
        if self._guild_needs_chunking(guild):
            asyncio.create_task(self._chunk_and_dispatch(guild, unavailable))
            return

        # Dispatch available if newly available
        if unavailable is False:
            self.dispatch('guild_available', guild)
        else:
            self.dispatch('guild_join', guild)

    def parse_guild_update(self, data) -> None:
        guild = self._get_guild(int(data['id']))
        if guild is not None:
            old_guild = copy.copy(guild)
            guild._from_data(data)
            self.dispatch('guild_update', old_guild, guild)
        else:
            _log.debug('GUILD_UPDATE 引用了一个未知的频道 ID：%s。丢弃。', data['id'])

    def parse_guild_delete(self, data) -> None:
        guild = self._get_guild(int(data['id']))
        if guild is None:
            _log.debug('GUILD_DELETE 引用了一个未知的频道 ID：%s。丢弃。', data['id'])
            return

        if data.get('unavailable', False):
            # GUILD_DELETE with unavailable being True means that the
            # guild that was available is now currently unavailable
            guild.unavailable = True
            self.dispatch('guild_unavailable', guild)
            return

        # do a cleanup of the messages cache
        if self._messages is not None:
            self._messages: Optional[Deque[Message]] = deque(
                (msg for msg in self._messages if msg.guild != guild), maxlen=self.max_messages
            )

        self._remove_guild(guild)
        self.dispatch('guild_remove', guild)

    def parse_audio_start(self, data) -> None:
        audio = AudioAction(data)
        self.dispatch('audio_start', audio)

    def parse_audio_finish(self, data) -> None:
        audio = AudioAction(data)
        self.dispatch('audio_stop', audio)

    def parse_audio_on_mic(self, data) -> None:
        audio = AudioAction(data)
        self.dispatch('mic_start', audio)

    def parse_audio_off_mic(self, data) -> None:
        audio = AudioAction(data)
        self.dispatch('mic_stop', audio)

    def parse_message_reaction_add(self, data) -> None:
        emoji = data['emoji']
        emoji_id = emoji.get('id')
        emoji = PartialEmoji.with_state(self, id=emoji_id, custom=True if emoji['type'] == '1' else False)
        raw = RawReactionActionEvent(data, emoji, 'REACTION_ADD')

        member_data = data.get('member')
        if member_data:
            guild = self._get_guild(raw.guild_id)
            if guild is not None:
                raw.member = Member(data=member_data, guild=guild, state=self)
            else:
                raw.member = None
        else:
            raw.member = None
        self.dispatch('raw_reaction_add', raw)

        # rich interface here
        message = self._get_message(raw.id)
        if message is not None:
            emoji = self._upgrade_partial_emoji(emoji)
            reaction = message._add_reaction(data, emoji, raw.user_id)
            user = raw.member or self._get_reaction_user(message.channel, raw.user_id)

            if user:
                self.dispatch('reaction_add', reaction, user)

    def parse_message_reaction_remove_all(self, data) -> None:
        raw = RawReactionClearEvent(data)
        self.dispatch('raw_reaction_clear', raw)

        message = self._get_message(raw.id)
        if message is not None:
            old_reactions = message.reactions.copy()
            message.reactions.clear()
            self.dispatch('reaction_clear', message, old_reactions)

    def parse_message_reaction_remove(self, data) -> None:
        emoji = data['emoji']
        emoji_id = emoji.get('id')
        emoji = PartialEmoji.with_state(self, id=emoji_id, custom=True if emoji['type'] == '1' else False)
        raw = RawReactionActionEvent(data, emoji, 'REACTION_REMOVE')
        self.dispatch('raw_reaction_remove', raw)

        message = self._get_message(raw.id)
        if message is not None:
            emoji = self._upgrade_partial_emoji(emoji)
            try:
                reaction = message._remove_reaction(data, emoji, raw.user_id)
            except (AttributeError, ValueError):  # eventual consistency lol
                pass
            else:
                user = self._get_reaction_user(message.channel, raw.user_id)
                if user:
                    self.dispatch('reaction_remove', reaction, user)

    def parse_message_reaction_remove_emoji(self, data) -> None:
        emoji = data['emoji']
        emoji_id = emoji.get('id')
        emoji = PartialEmoji.with_state(self, id=emoji_id, custom=True if emoji['type'] == '1' else False)
        raw = RawReactionClearEmojiEvent(data, emoji)
        self.dispatch('raw_reaction_clear_emoji', raw)

        message = self._get_message(raw.id)
        if message is not None:
            try:
                reaction = message._clear_emoji(emoji)
            except (AttributeError, ValueError):  # eventual consistency lol
                pass
            else:
                if reaction:
                    self.dispatch('reaction_clear_emoji', reaction)

    def get_channel(self, id: Optional[int]) -> Optional[Union[Channel]]:
        if id is None:
            return None

        for guild in self.guilds:
            channel = guild._resolve_channel(id)
            if channel is not None:
                return channel

    def create_message(
            self, *, channel: Union[TextChannel, PartialMessageable, DMChannel], data: MessagePayload, direct: bool
    ) -> Message:
        return Message(state=self, channel=channel, data=data, direct=direct)

    def _upgrade_partial_emoji(self, emoji: PartialEmoji) -> Union[PartialEmoji, str]:
        emoji_id = emoji.id
        if not emoji_id:
            return emoji.name

        return emoji

    def _get_reaction_user(self, channel: MessageableChannel, user_id: int) -> Optional[Union[User, Member]]:
        if isinstance(channel, TextChannel):
            return channel.guild.get_member(user_id)
        return self.get_user(user_id)


class AutoShardedConnectionState(ConnectionState):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.shard_ids: Union[List[int], range] = []
        self.shards_launched: asyncio.Event = asyncio.Event()

    def _update_message_references(self) -> None:
        # self._messages won't be None when this is called
        for msg in self._messages:  # type: ignore
            if not msg.guild:
                continue

            new_guild = self._get_guild(msg.guild.id)
            if new_guild is not None and new_guild is not msg.guild:
                channel_id = msg.channel.id
                channel = new_guild._resolve_channel(channel_id) or Object(id=channel_id)
                # channel will either be a TextChannel, Thread or Object
                msg._rebind_cached_references(new_guild, channel)  # type: ignore

    async def chunker(
            self,
            guild_id: int,
            query: str = '',
            limit: int = 0,
            presences: bool = False,
            *,
            shard_id: Optional[int] = None,
            nonce: Optional[str] = None,
    ) -> None:
        ws = self._get_websocket(guild_id, shard_id=shard_id)
        await ws.request_chunks(guild_id, query=query, limit=limit, presences=presences, nonce=nonce)

    async def _delay_ready(self) -> None:
        await self.shards_launched.wait()
        processed = []
        max_concurrency = len(self.shard_ids) * 2
        current_bucket = []
        while True:
            # this snippet of code is basically waiting N seconds
            # until the last GUILD_CREATE was sent
            try:
                guild = await asyncio.wait_for(self._ready_state.get(), timeout=self.guild_ready_timeout)
            except asyncio.TimeoutError:
                break
            else:
                if self._guild_needs_chunking(guild):
                    _log.debug('频道 ID %d 需要分块，将在后台完成。', guild.id)
                    if len(current_bucket) >= max_concurrency:
                        try:
                            await utils.sane_wait_for(current_bucket, timeout=max_concurrency * 70.0)
                        except asyncio.TimeoutError:
                            fmt = '分片 ID %s 无法等待来自长度为 %d 的子存储桶的块'
                            _log.warning(fmt, guild.shard_id, len(current_bucket))
                        finally:
                            current_bucket = []

                    # Chunk the guild in the background while we wait for GUILD_CREATE streaming
                    future = asyncio.ensure_future(self.chunk_guild(guild))
                    current_bucket.append(future)
                else:
                    future = self.loop.create_future()
                    future.set_result([])

                processed.append((guild, future))

        guilds = sorted(processed, key=lambda g: g[0].shard_id)
        for shard_id, info in itertools.groupby(guilds, key=lambda g: g[0].shard_id):
            children, futures = zip(*info)
            # 110 reqs/minute w/ 1 req/guild plus some buffer
            timeout = 61 * (len(children) / 110)
            try:
                await utils.sane_wait_for(futures, timeout=timeout)
            except asyncio.TimeoutError:
                _log.warning(
                    '分片 ID %s 无法等待 %d 个公会的块（超时 = %.2f）', shard_id, timeout, len(guilds)
                )
            for guild in children:
                if guild.unavailable is False:
                    self.dispatch('guild_available', guild)
                else:
                    self.dispatch('guild_join', guild)

            self.dispatch('shard_ready', shard_id)

        # remove the state
        try:
            del self._ready_state
        except AttributeError:
            pass  # already been deleted somehow

        # regular users cannot shard so we won't worry about it here.

        # clear the current task
        self._ready_task = None

        # dispatch the event
        self.call_handlers('ready')
        self.dispatch('ready')

    async def parse_ready(self, data) -> None:
        if not hasattr(self, '_ready_state'):
            self._ready_state = asyncio.Queue()

        self.user = user = ClientUser(state=self, data=data['user'])
        # self._users is a list of Users, we're setting a ClientUser
        self._users[user.id] = user  # type: ignore

        if self.application_id is None:
            try:
                application = data['application']
            except KeyError:
                pass
            else:
                self.application_id = application.get('id')

        result = await self.http.get_guilds()

        for guild_data in result:
            guild = self._add_guild_from_data(guild_data)
            await guild.fill_in()

        if self._messages:
            self._update_message_references()

        self.dispatch('connect')
        self.dispatch('shard_connect', data['__shard_id__'])

        if self._ready_task is None:
            self._ready_task = asyncio.create_task(self._delay_ready())

    def parse_resumed(self, data) -> None:
        self.dispatch('resumed')
        self.dispatch('shard_resumed', data['__shard_id__'])
