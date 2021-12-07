from __future__ import annotations

import copy
from datetime import datetime
from typing import overload, Optional, Union, List, TYPE_CHECKING, TypeVar, Dict, Any

from . import Guild, utils
from .channel import CategoryChannel, TextChannel, PartialMessageable
from .enum import ChannelType
from .error import InvalidArgument
from .member import Member
from .mention import AllowedMentions
from .role import Role
from .user import User
from .utils import MISSING

if TYPE_CHECKING:
    from .state import ConnectionState
    from .message import Message
    from .types.channel import (
        Channel as ChannelPayload,
        GuildChannel as GuildChannelPayload,
    )

    PartialMessageableChannel = Union[TextChannel, PartialMessageable]
    MessageableChannel = Union[PartialMessageableChannel]

__all__ = ('Messageable',
           'GuildChannel')


class _Undefined:
    def __repr__(self) -> str:
        return 'see-below'


_undefined: Any = _Undefined()


class Messageable:
    __slots__ = ()
    _state: ConnectionState

    async def _get_channel(self) -> MessageableChannel:
        raise NotImplementedError

    @overload
    async def send(
            self,
            content: Optional[str] = ...,
            *,
            tts: bool = ...,
            nonce: Union[str, int] = ...,
            allowed_mentions: AllowedMentions = ...,
            reference: Union[Message] = ...,
            mention_author: bool = ...,
    ) -> Message:
        ...

    async def send(
            self,
            content=None,
            *,
            tts=None,
            nonce=None,
            allowed_mentions=None,
            reference=None,
            mention_author=None,
    ):

        channel = await self._get_channel()
        state = self._state
        content = str(content) if content is not None else None

        if allowed_mentions is not None:
            if state.allowed_mentions is not None:
                allowed_mentions = state.allowed_mentions.merge(allowed_mentions).to_dict()
            else:
                allowed_mentions = allowed_mentions.to_dict()
        else:
            allowed_mentions = state.allowed_mentions and state.allowed_mentions.to_dict()

        if mention_author is not None:
            allowed_mentions = allowed_mentions or AllowedMentions().to_dict()
            allowed_mentions['replied_user'] = bool(mention_author)

        if reference is not None:
            try:
                reference = reference.to_message_reference_dict()
            except AttributeError:
                raise InvalidArgument(
                    'reference parameter must be Message, MessageReference, or PartialMessage') from None

        data = await state.http.send_message(
            channel.id,
            content,
            tts=tts,
            nonce=nonce,
            allowed_mentions=allowed_mentions,
            message_reference=reference,
        )

        ret = state.create_message(channel=channel, data=data)
        return ret

    async def fetch_message(self, id: int, /) -> Message:
        """|coro|
        Retrieves a single :class:`~discord.Message` from the destination.
        Parameters
        ------------
        id: :class:`int`
            The message ID to look for.
        Raises
        --------
        ~discord.NotFound
            The specified message was not found.
        ~discord.Forbidden
            You do not have the permissions required to get a message.
        ~discord.HTTPException
            Retrieving the message failed.
        Returns
        --------
        :class:`~discord.Message`
            The message asked for.
        """
        id = id
        channel = await self._get_channel()
        data = await self._state.http.get_message(channel.id, id)
        return self._state.create_message(channel=channel, data=data)


GCH = TypeVar('GCH', bound='GuildChannel')


class GuildChannel:
    __slots__ = ()

    id: int
    name: str
    guild: Guild
    type: ChannelType
    position: int
    category_id: Optional[int]
    _state: ConnectionState

    if TYPE_CHECKING:
        def __init__(self, *, state: ConnectionState, guild: Guild, data: Dict[str, Any]):
            ...

    def __str__(self) -> str:
        return self.name

    @property
    def _sorting_bucket(self) -> int:
        raise NotImplementedError

    def _update(self, guild: Guild, data: Dict[str, Any]) -> None:
        raise NotImplementedError

    async def _move(
            self,
            position: int,
            parent_id: Optional[Any] = None,
            *,
            reason: Optional[str],
    ) -> None:
        raise NotImplementedError
        if position < 0:
            raise InvalidArgument('Channel position cannot be less than 0.')

        http = self._state.http
        bucket = self._sorting_bucket
        channels: List[GuildChannel] = [c for c in self.guild.channels if c._sorting_bucket == bucket]

        channels.sort(key=lambda c: c.position)

        try:
            # remove ourselves from the channel list
            channels.remove(self)
        except ValueError:
            # not there somehow lol
            return
        else:
            index = next((i for i, c in enumerate(channels) if c.position >= position), len(channels))
            # add ourselves at our designated position
            channels.insert(index, self)

        payload = []
        for index, c in enumerate(channels):
            d: Dict[str, Any] = {'id': c.id, 'position': index}
            if parent_id is not _undefined and c.id == self.id:
                d.update(parent_id=parent_id)
            payload.append(d)

        await http.bulk_channel_update(self.guild.id, payload, reason=reason)

    async def _edit(self, options: Dict[str, Any], reason: Optional[str]) -> Optional[ChannelPayload]:
        raise NotImplementedError
        try:
            parent = options.pop('category')
        except KeyError:
            parent_id = _undefined
        else:
            parent_id = parent and parent.id

        try:
            options['rate_limit_per_user'] = options.pop('slowmode_delay')
        except KeyError:
            pass

        try:
            rtc_region = options.pop('rtc_region')
        except KeyError:
            pass
        else:
            options['rtc_region'] = None if rtc_region is None else str(rtc_region)

        try:
            video_quality_mode = options.pop('video_quality_mode')
        except KeyError:
            pass
        else:
            options['video_quality_mode'] = int(video_quality_mode)

        try:
            position = options.pop('position')
        except KeyError:
            if parent_id is not _undefined:
                options['parent_id'] = parent_id
        else:
            await self._move(position, parent_id=parent_id, reason=reason)

        try:
            ch_type = options['type']
        except KeyError:
            pass
        else:
            if not isinstance(ch_type, ChannelType):
                raise InvalidArgument('type field must be of type ChannelType')
            options['type'] = ch_type.value

        if options:
            return await self._state.http.edit_channel(self.id, reason=reason, **options)

    @property
    def mention(self) -> str:
        """:class:`str`: The string that allows you to mention the channel."""
        return f'<#{self.id}>'

    @property
    def category(self) -> Optional[CategoryChannel]:
        """Optional[:class:`~discord.CategoryChannel`]: The category this channel belongs to.
        If there is no category then this is ``None``.
        """
        return self.guild.get_channel(self.category_id)  # type: ignore

    async def delete(self, *, reason: Optional[str] = None) -> None:
        raise NotImplementedError
        await self._state.http.delete_channel(self.id, reason=reason)

    async def _clone_impl(
            self: GCH,
            base_attrs: Dict[str, Any],
            *,
            name: Optional[str] = None,
            reason: Optional[str] = None,
    ) -> GCH:
        raise NotImplementedError
        base_attrs['parent_id'] = self.category_id
        base_attrs['name'] = name or self.name
        guild_id = self.guild.id
        cls = self.__class__
        data = await self._state.http.create_channel(guild_id, self.type.value, reason=reason, **base_attrs)
        obj = cls(state=self._state, guild=self.guild, data=data)

        # temporarily add it to the cache
        self.guild._channels[obj.id] = obj  # type: ignore
        return obj

    async def clone(self: GCH, *, name: Optional[str] = None, reason: Optional[str] = None) -> GCH:
        raise NotImplementedError

    @overload
    async def move(
            self,
            *,
            beginning: bool,
            offset: int = MISSING,
            category: Optional[int] = MISSING,
            sync_permissions: bool = MISSING,
            reason: Optional[str] = MISSING,
    ) -> None:
        ...

    @overload
    async def move(
            self,
            *,
            end: bool,
            offset: int = MISSING,
            category: Optional[int] = MISSING,
            sync_permissions: bool = MISSING,
            reason: str = MISSING,
    ) -> None:
        ...

    @overload
    async def move(
            self,
            *,
            before: int,
            offset: int = MISSING,
            category: Optional[int] = MISSING,
            sync_permissions: bool = MISSING,
            reason: str = MISSING,
    ) -> None:
        ...

    @overload
    async def move(
            self,
            *,
            after: int,
            offset: int = MISSING,
            category: Optional[int] = MISSING,
            sync_permissions: bool = MISSING,
            reason: str = MISSING,
    ) -> None:
        ...

    async def move(self, **kwargs) -> None:
        if not kwargs:
            return

        beginning, end = kwargs.get('beginning'), kwargs.get('end')
        before, after = kwargs.get('before'), kwargs.get('after')
        offset = kwargs.get('offset', 0)
        if sum(bool(a) for a in (beginning, end, before, after)) > 1:
            raise InvalidArgument('Only one of [before, after, end, beginning] can be used.')

        bucket = self._sorting_bucket
        parent_id = kwargs.get('category', MISSING)
        # fmt: off
        channels: List[GuildChannel]
        if parent_id not in (MISSING, None):
            parent_id = parent_id.id
            channels = [ch for ch in self.guild.channels
                        if ch._sorting_bucket == bucket and ch.category_id == parent_id]
        else:
            channels = [ch for ch in self.guild.channels
                        if ch._sorting_bucket == bucket and ch.category_id == self.category_id]
        # fmt: on

        channels.sort(key=lambda c: (c.position, c.id))

        try:
            # Try to remove ourselves from the channel list
            channels.remove(self)
        except ValueError:
            # If we're not there then it's probably due to not being in the category
            pass

        index = None
        if beginning:
            index = 0
        elif end:
            index = len(channels)
        elif before:
            index = next((i for i, c in enumerate(channels) if c.id == before.id), None)
        elif after:
            index = next((i + 1 for i, c in enumerate(channels) if c.id == after.id), None)

        if index is None:
            raise InvalidArgument('Could not resolve appropriate move position')

        channels.insert(max((index + offset), 0), self)
        payload = []
        lock_permissions = kwargs.get('sync_permissions', False)
        reason = kwargs.get('reason')
        for index, channel in enumerate(channels):
            d = {'id': channel.id, 'position': index}
            if parent_id is not MISSING and channel.id == self.id:
                d.update(parent_id=parent_id, lock_permissions=lock_permissions)
            payload.append(d)

        await self._state.http.bulk_channel_update(self.guild.id, payload, reason=reason)
