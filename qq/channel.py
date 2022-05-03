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
from typing import TYPE_CHECKING, Iterable, Optional, List, overload, Callable, TypeVar, Type, Tuple, Union

from . import abc, utils
from .enum import ChannelType, try_enum
from .error import ClientException
from .mixins import Hashable
from .object import Object
from .schedule import Schedule

__all__ = (
    'TextChannel',
    'VoiceChannel',
    'LiveChannel',
    'AppChannel',
    'CategoryChannel',
    'ThreadChannel',
    'PartialMessageable',
    'DMChannel'
)

from .utils import MISSING

if TYPE_CHECKING:
    from .user import *
    from .member import Member
    from .message import Message, PartialMessage
    from .state import ConnectionState
    from .guild import Guild, GuildChannel as GuildChannelType
    from .types.channel import (
        TextChannel as TextChannelPayload,
        VoiceChannel as VoiceChannelPayload,
        CategoryChannel as CategoryChannelPayload,
        LiveChannel as LiveChannelPayload,
        AppChannel as AppChannelPayload,
        ThreadChannel as ThreadChannelPayload,
        DMChannel as DMChannelPayload,
    )


async def _single_delete_strategy(messages: Iterable[Message]):
    for m in messages:
        await m.delete()


class TextChannel(abc.Messageable, abc.GuildChannel, Hashable):
    """代表 QQ 频道中的文字子频道

    .. container:: operations
        .. describe:: x == y

            检查两个子频道是否相等。

        .. describe:: x != y

            检查两个子频道是否不相等。

        .. describe:: hash(x)

            返回子频道的哈希值。

        .. describe:: str(x)

            返回子频道的名称。

    Attributes
    -----------
    name: :class:`str`
        子频道的名称。
    guild: :class:`Guild`
        子频道所属的频道。
    id: :class:`int`
        子频道 ID。
    private_type: :class:`int`
        子频道私密类型。

        +----+---------------------+
        | 值 | 含义                |
        +----+---------------------+
        | 0  | 公开频道            |
        +----+---------------------+
        | 1  | 群主管理员可见      |
        +----+---------------------+
        | 2  | 群主管理员+指定成员 |
        +----+---------------------+

    category_id: Optional[:class:`int`]
        这个子频道属于的分类频道，如果没有则返回 ``None`` 。
    position: :class:`int`
        在子频道列表中的位置。 这是一个从 0 开始的数字。例如顶部子频道是位置 0。
    last_message_id: Optional[:class:`int`]
        发送到此通道的消息的最后一个消息 ID。 它可能 *不* 指向现有的或有效的消息。

    """

    __slots__ = (
        'name',
        'id',
        'guild',
        '_state',
        'category_id',
        'position',
        '_type',
        'last_message_id',
        'private_type'
    )

    def __init__(self, *, state: ConnectionState, guild: Guild, data: TextChannelPayload):
        self._state: ConnectionState = state
        self.id: int = int(data['id'])
        self._type: int = data['type']
        self.last_message_id: Optional[int] = None
        self._update(guild, data)

    def __repr__(self) -> str:
        attrs = [
            ('id', self.id),
            ('name', self.name),
            ('position', self.position),
            ('category_id', self.category_id),
        ]
        joined = ' '.join('%s=%r' % t for t in attrs)
        return f'<{self.__class__.__name__} {joined}>'

    def _update(self, guild: Guild, data: TextChannelPayload) -> None:
        self.guild: Guild = guild
        self.name: str = data['name']
        self.category_id: Optional[int] = int(data.get('parent_id')) if 'parent_id' in data else self.category_id
        self.position: int = data['position'] if 'position' in data else self.position
        self._type: int = data.get('type', self._type)
        self.private_type: int = data.get('private_type')

    async def _get_channel(self):
        return self, False

    @property
    def type(self) -> ChannelType:
        return try_enum(ChannelType, self._type)

    @property
    def _sorting_bucket(self) -> int:
        return ChannelType.text.value

    @property
    def members(self) -> List[Member]:
        """List[:class:`Member`]: 返回可以看到此子频道的所有成员。"""
        return [m for m in self.guild.members]

    def get_partial_message(self, message_id: int, /) -> PartialMessage:
        """从消息 ID 创建一个 :class:`PartialMessage`。
        如果你想处理消息并且只有它的 ID 而不进行不必要的 API 调用，这将非常有用。

        Parameters
        ------------
        message_id: :class:`int`
            要为其创建部分消息的消息 ID。
        Returns
        ---------
        :class:`PartialMessage`
            部分消息。
        """

        from .message import PartialMessage

        return PartialMessage(channel=self, id=message_id)

    @overload
    async def edit(
            self,
            *,
            reason: Optional[str] = ...,
            name: str = ...,
            position: int = ...,
            category: Optional[CategoryChannel] = ...,
            type: ChannelType = ...,
    ) -> Optional[TextChannel]:
        ...

    @overload
    async def edit(self) -> Optional[TextChannel]:
        ...

    async def edit(self, *, reason=None, **options):
        """|coro|
        编辑子频道。

        Parameters
        ----------
        name: :class:`str`
            新频道名称。
        position: :class:`int`
            新频道的位置。
        category: Optional[:class:`CategoryChannel`]
            此频道的新类别。可以是 ``None`` 以删除类别。
        type: :class:`ChannelType`
            更改此文本频道的类型。 不保证能够成功转换。
        reason: Optional[:class:`str`]
            编辑此频道的原因。显示在审计日志中。

        Raises
        ------
        InvalidArgument
            如果 position 小于 0 或大于子频道数。
        Forbidden
            你没有编辑频道的权限。
        HTTPException
            编辑频道失败。
        Returns
        --------
        Optional[:class:`.TextChannel`]
            新编辑的文本通道。如果编辑只是位置性的，则返回 ``None`` 。
        """

        payload = await self._edit(options, reason=reason)
        if payload is not None:
            # the payload will always be the proper channel payload
            return self.__class__(state=self._state, guild=self.guild, data=payload)  # type: ignore

    @utils.copy_doc(abc.GuildChannel.clone)
    async def clone(self, *, name: Optional[str] = None, reason: Optional[str] = None) -> TextChannel:
        return await self._clone_impl(
            {}, name=name, reason=reason
        )

    async def delete_messages(self, messages: Iterable[Message]) -> None:
        """|coro|
        删除消息列表。这类似于 :meth:`Message.delete`，除了它批量删除多条消息。
        作为一种特殊情况，如果消息数为 0，则什么也不做。如果消息数为 1，则完成单个消息删除。
        如果超过两个，则使用批量删除。你不能批量删除超过 100 条消息或超过 14 天的消息。

        Parameters
        -----------
        messages: Iterable[:class:`qq.Message`]
            一个可迭代的消息，表示要批量删除的消息。

        Raises
        ------
        ClientException
            要删除的消息数量超过 100 条。
        Forbidden
            你没有删除消息的适当权限。
        NotFound
            如果单次删除，则该消息已被删除。
        HTTPException
            删除消息失败。
        """
        if not isinstance(messages, (list, tuple)):
            messages = list(messages)

        if len(messages) == 0:
            return  # do nothing

        if len(messages) == 1:
            message_id: str = messages[0].id
            await self._state.http.delete_message(self.id, message_id)
            return

        if len(messages) > 100:
            raise ClientException('最多只能批量删除 100 条消息')

        message_ids = [m.id for m in messages]
        await self._state.http.delete_messages(self.id, message_ids)

    async def purge(
            self,
            *,
            limit: Optional[int] = 100,
            check: Callable[[Message], bool] = MISSING,
            before: Optional[datetime.datetime] = None,
            after: Optional[datetime.datetime] = None,
            around: Optional[datetime.datetime] = None,
            oldest_first: Optional[bool] = False,
            bulk: bool = True,
    ) -> List[Message]:
        """|coro|
        清除符合检查函数 ``check`` 给定标准的消息列表。
        如果未提供 ``check`` ，则所有消息都将被删除，一视同仁。

        Examples
        ---------
        删除机器人的消息: ::

            def is_me(m):
                return m.author == client.user
            deleted = await channel.purge(limit=100, check=is_me)
            await channel.send(f'已删除 {len(deleted)} 个消息')

        Parameters
        -----------
        limit: Optional[:class:`int`]
            要搜索的消息数。这不是将被删除的消息数，尽管可以是。
        check: Callable[[:class:`Message`], :class:`bool`]
            用于检查是否应删除消息的功能。它必须将 Message 作为其唯一参数。
        before: Optional[:class:`datetime.datetime`]
            与 :meth:`history` 中的 ``before`` 相同。
        after: Optional[:class:`datetime.datetime`]
            与 :meth:`history` 中的 ``after`` 相同。
        around: Optional[Union[:class:`abc.Snowflake`, :class:`datetime.datetime`]]
            与 :meth:`history`中的 ``around`` 相同。
        oldest_first: Optional[:class:`bool`]
            与 :meth:`history` 中的 ``oldest_first`` 相同。
        bulk: :class:`bool`
            如果 ``True`` ，使用批量删除。

        Raises
        -------
        Forbidden
            你没有执行所需操作的适当权限。
        HTTPException
            清除消息失败。

        Returns
        --------
        List[:class:`.Message`]
            已删除的消息列表。
        """

        if check is MISSING:
            check = lambda m: True

        iterator = self.history(limit=limit, before=before, after=after, oldest_first=oldest_first, around=around)
        ret: List[Message] = []
        count = 0
        strategy = self.delete_messages if bulk else _single_delete_strategy

        async for message in iterator:
            if count == 100:
                to_delete = ret[-100:]
                await strategy(to_delete)
                count = 0
                await asyncio.sleep(1)

            if not check(message):
                continue

            count += 1
            ret.append(message)

        # SOme messages remaining to poll
        if count >= 2:
            # more than 2 messages -> bulk delete
            to_delete = ret[-count:]
            await strategy(to_delete)
        elif count == 1:
            # delete a single message
            await ret[-1].delete()

        return ret

    async def unpin(self, reason: Optional[str] = None):
        """
        删除所有此子频道的公告。

        Parameters
        -----------
        reason: Optional[:class:`str`]
            删除公告的原因。

        Raises
        -------
        Forbidden
            你没有足够权限删除公告。
        NotFound
            消息或频道无法被找到，可能被删除了.
        HTTPException
            删除公告失败。
        """
        await self._state.http.channel_unpin_message(self.id, 'all', reason=reason)

    async def send_guide(self, content: str):
        """
        发送主动消息引导信息。

        Parameters
        -----------
        content: :class:`str`
            要发送的内容。

        Raises
        -------
        Forbidden
            你没有足够权限发送。
        HTTPException
            发送失败。
        """
        await self._state.http.send_guide(self.id, content)


class VoiceChannel(abc.GuildChannel, Hashable):
    """表示 QQ 语音子频道。

    .. container:: operations

        .. describe:: x == y

            检查两个子频道是否相等。

        .. describe:: x != y

            检查两个子频道是否不相等。

        .. describe:: hash(x)

            返回子频道的哈希值。

        .. describe:: str(x)

            返回子频道的名称。

    Attributes
    -----------
    name: :class:`str`
        子频道名称。
    guild: :class:`Guild`
        子频道所属的频道。
    id: :class:`int`
        频道 ID。
    private_type: :class:`int`
        子频道私密类型。

        +----+---------------------+
        | 值 | 含义                |
        +----+---------------------+
        | 0  | 公开频道            |
        +----+---------------------+
        | 1  | 群主管理员可见      |
        +----+---------------------+
        | 2  | 群主管理员+指定成员 |
        +----+---------------------+

    position: :class:`int`
        在类别列表中的位置。 这是一个从 0 开始的数字。例如顶部频道是位置 0。
    """
    __slots__ = (
        'name',
        'id',
        'guild',
        '_state',
        'position',
        'category_id',
        'private_type'
    )

    def __init__(self, *, state: ConnectionState, guild: Guild, data: VoiceChannelPayload):
        self._state: ConnectionState = state
        self.id: int = int(data['id'])
        self._update(guild, data)

    def _update(self, guild: Guild, data: VoiceChannelPayload) -> None:
        self.guild = guild
        self.name: str = data['name']
        self.category_id: Optional[int] = int(data.get('parent_id'))
        self.position: int = data['position']
        self.private_type: int = data.get('private_type')

    def __repr__(self) -> str:
        attrs = [
            ('id', self.id),
            ('name', self.name),
            ('position', self.position),
            ('category_id', self.category_id),
        ]
        joined = ' '.join('%s=%r' % t for t in attrs)
        return f'<{self.__class__.__name__} {joined}>'

    @property
    def type(self) -> ChannelType:
        """:class:`ChannelType`: 子频道的QQ类型。"""
        return ChannelType.voice

    @utils.copy_doc(abc.GuildChannel.clone)
    async def clone(self, *, name: Optional[str] = None, reason: Optional[str] = None) -> VoiceChannel:
        return await self._clone_impl({}, name=name, reason=reason)

    @overload
    async def edit(
            self,
            *,
            name: str = ...,
            position: int = ...,
            category: Optional[CategoryChannel] = ...,
            reason: Optional[str] = ...,
    ) -> Optional[VoiceChannel]:
        ...

    @overload
    async def edit(self) -> Optional[VoiceChannel]:
        ...

    async def edit(self, *, reason=None, **options):
        """|coro|
        编辑频道。

        Parameters
        ----------
        name: :class:`str`
            新频道的名称。
        position: :class:`int`
            新频道的位置。
        category: Optional[:class:`CategoryChannel`]
            此频道的新类别。可以是 ``None`` 以删除类别。
        reason: Optional[:class:`str`]
            编辑此频道的原因。显示在审计日志中。

        Raises
        ------
        InvalidArgument
            如果权限覆盖信息格式不正确。
        Forbidden
            你没有编辑频道的权限。
        HTTPException
            编辑频道失败。

        Returns
        --------
        Optional[:class:`.VoiceChannel`]
            新编辑的语音通道。如果编辑只是位置性的，则返回 ``None`` 。
        """

        payload = await self._edit(options, reason=reason)
        if payload is not None:
            # the payload will always be the proper channel payload
            return self.__class__(state=self._state, guild=self.guild, data=payload)  # type: ignore


class LiveChannel(abc.GuildChannel, Hashable, abc.Messageable):
    """表示 QQ 直播子频道。

    .. container:: operations

        .. describe:: x == y

            检查两个子频道是否相等。

        .. describe:: x != y

            检查两个子频道是否不相等。

        .. describe:: hash(x)

            返回子频道的哈希值。

        .. describe:: str(x)

            返回子频道的名称。

    Attributes
    -----------
    name: :class:`str`
        子频道名称。
    guild: :class:`Guild`
        子频道所属的频道。
    id: :class:`int`
        频道 ID。
    private_type: :class:`int`
        子频道私密类型。

        +----+---------------------+
        | 值 | 含义                |
        +----+---------------------+
        | 0  | 公开频道            |
        +----+---------------------+
        | 1  | 群主管理员可见      |
        +----+---------------------+
        | 2  | 群主管理员+指定成员 |
        +----+---------------------+

    position: :class:`int`
        在类别列表中的位置。 这是一个从 0 开始的数字。例如顶部频道是位置 0。
    """

    __slots__ = (
        'name',
        'id',
        'guild',
        '_state',
        'position',
        'category_id',
        'private_type'
    )

    def __init__(self, *, state: ConnectionState, guild: Guild, data: LiveChannelPayload):
        self._state: ConnectionState = state
        self.id: int = int(data['id'])
        self._update(guild, data)

    def _update(self, guild: Guild, data: LiveChannelPayload) -> None:
        self.guild = guild
        self.name: str = data['name']
        self.category_id: Optional[int] = int(data.get('parent_id'))
        self.position: int = data['position']
        self.private_type: int = data.get('private_type')

    def __repr__(self) -> str:
        attrs = [
            ('id', self.id),
            ('name', self.name),
            ('position', self.position),
            ('category_id', self.category_id),
        ]
        joined = ' '.join('%s=%r' % t for t in attrs)
        return f'<{self.__class__.__name__} {joined}>'


class AppChannel(abc.GuildChannel, Hashable):
    """表示 QQ 应用子频道。

    .. container:: operations

        .. describe:: x == y

            检查两个子频道是否相等。

        .. describe:: x != y

            检查两个子频道是否不相等。

        .. describe:: hash(x)

            返回子频道的哈希值。

        .. describe:: str(x)

            返回子频道的名称。

    Attributes
    -----------
    name: :class:`str`
        子频道名称。
    guild: :class:`Guild`
        子频道所属的频道。
    id: :class:`int`
        频道 ID。
    private_type: :class:`int`
        子频道私密类型。

        +----+---------------------+
        | 值 | 含义                |
        +----+---------------------+
        | 0  | 公开频道            |
        +----+---------------------+
        | 1  | 群主管理员可见      |
        +----+---------------------+
        | 2  | 群主管理员+指定成员 |
        +----+---------------------+

    position: :class:`int`
        在类别列表中的位置。 这是一个从 0 开始的数字。例如顶部频道是位置 0。
    """
    __slots__ = (
        'name',
        'id',
        'guild',
        '_state',
        'position',
        'category_id',
        'private_type'
    )

    def __init__(self, *, state: ConnectionState, guild: Guild, data: AppChannelPayload):
        self._state: ConnectionState = state
        self.id: int = int(data['id'])
        self._update(guild, data)

    def _update(self, guild: Guild, data: AppChannelPayload) -> None:
        self.guild = guild
        self.name: str = data['name']
        self.category_id: Optional[int] = int(data.get('parent_id'))
        self.position: int = data['position']
        self.private_type: int = data.get('private_type')

    def __repr__(self) -> str:
        attrs = [
            ('id', self.id),
            ('name', self.name),
            ('position', self.position),
            ('category_id', self.category_id),
        ]
        joined = ' '.join('%s=%r' % t for t in attrs)
        return f'<{self.__class__.__name__} {joined}>'

    async def create_schedule(
            self,
            name: str,
            start: Union[datetime.datetime, float],
            end: Union[datetime.datetime, float],
            jump_channel: GuildChannelType,
            remind_type: str,
            description: Optional[str] = None,
    ) -> Schedule:
        """返回具有给定 path 和 method 的权限。

        Parameters
        -----------
        name: :class:`str`
            成员所属的频道。
        description: Optional[:class:`str`]
        start: Union[:class:`datetime.datetime`, :class:`float`]
            日程开始的时间。
        end: Union[:class:`datetime.datetime`, :class:`float`]
            日程开始的时间。
        jump_channel: :class:`GuildChannel`
            日程开始的时间。
        remind_type: :class:`str`
            日程提醒类型。

            +-----------+--------------+
            | 提醒类型 id	  | 描述           |
            +===========+==============+
            | 0         | 不提醒          |
            | 1         | 开始时提醒        |
            | 2         | 开始前 5 分钟提醒   |
            | 3         | 开始前 15 分钟提醒  |
            | 4         | 开始前 30 分钟提醒  |
            | 5         | 开始前 60 分钟提醒  |
            +-----------+--------------+


        Returns
        --------
        Optional[:class:`Schedule`]
            Role 或如果未找到，则  ``None`` 。
        """
        schedule = await self._state.http.create_schedule(
            channel_id=self.id,
            name=name,
            start_timestamp=start,
            end_timestamp=end,
            jump_channel_id=jump_channel.id,
            remind_type=remind_type,
            description=description
        )

        return Schedule(data=schedule, state=self._state, guild=self.guild, channel=self)


class ThreadChannel(abc.GuildChannel, Hashable):
    """表示 QQ 论坛子频道。

    .. container:: operations

        .. describe:: x == y

            检查两个子频道是否相等。

        .. describe:: x != y

            检查两个子频道是否不相等。

        .. describe:: hash(x)

            返回子频道的哈希值。

        .. describe:: str(x)

            返回子频道的名称。

    Attributes
    -----------
    name: :class:`str`
        子频道名称。
    guild: :class:`Guild`
        子频道所属的频道。
    id: :class:`int`
        频道 ID。
    private_type: :class:`int`
        子频道私密类型。

        +----+---------------------+
        | 值 | 含义                |
        +----+---------------------+
        | 0  | 公开频道            |
        +----+---------------------+
        | 1  | 群主管理员可见      |
        +----+---------------------+
        | 2  | 群主管理员+指定成员 |
        +----+---------------------+

    position: :class:`int`
        在类别列表中的位置。 这是一个从 0 开始的数字。例如顶部频道是位置 0。
    """
    __slots__ = (
        'name',
        'id',
        'guild',
        '_state',
        'position',
        'category_id',
        'private_type'
    )

    def __init__(self, *, state: ConnectionState, guild: Guild, data: ThreadChannelPayload):
        self._state: ConnectionState = state
        self.id: int = int(data['id'])
        self._update(guild, data)

    def _update(self, guild: Guild, data: ThreadChannelPayload) -> None:
        self.guild = guild
        self.name: str = data['name']
        self.category_id: Optional[int] = int(data.get('parent_id'))
        self.position: int = data['position']
        self.private_type: int = data.get('private_type')

    def __repr__(self) -> str:
        attrs = [
            ('id', self.id),
            ('name', self.name),
            ('position', self.position),
            ('category_id', self.category_id),
        ]
        joined = ' '.join('%s=%r' % t for t in attrs)
        return f'<{self.__class__.__name__} {joined}>'


class CategoryChannel(abc.GuildChannel, Hashable):
    """表示 QQ 频道类别。
    这些对于将频道分组到逻辑区间很有用。

    .. container:: operations

        .. describe:: x == y

            检查两个频道是否相等。

        .. describe:: x != y

            检查两个频道是否不相等。

        .. describe:: hash(x)

            返回类别的哈希值。

        .. describe:: str(x)

            返回类别的名称。

    Attributes
    -----------
    name: :class:`str`
        类别名称。
    guild: :class:`Guild`
        类别所属的公会。
    id: :class:`int`
        类别频道 ID。
    private_type: :class:`int`
        子频道私密类型。

        +----+---------------------+
        | 值 | 含义                |
        +----+---------------------+
        | 0  | 公开频道            |
        +----+---------------------+
        | 1  | 群主管理员可见      |
        +----+---------------------+
        | 2  | 群主管理员+指定成员 |
        +----+---------------------+

    position: :class:`int`
        在类别列表中的位置。 这是一个从 0 开始的数字。例如顶部频道是位置 0。
    """

    __slots__ = ('name', 'id', 'guild', '_state', 'position', 'category_id', 'private_type')

    def __init__(self, *, state: ConnectionState, guild: Guild, data: CategoryChannelPayload):
        self._state: ConnectionState = state
        self.id: int = int(data['id'])
        self._update(guild, data)

    def __repr__(self) -> str:
        return f'<CategoryChannel id={self.id} name={self.name!r} position={self.position}>'

    def _update(self, guild: Guild, data: CategoryChannelPayload) -> None:
        self.guild: Guild = guild
        self.name: str = data['name']
        self.category_id: Optional[int] = int(data.get('parent_id', 0))
        self.position: int = data['position']
        self.private_type: int = data.get('private_type')

    @property
    def _sorting_bucket(self) -> int:
        return ChannelType.category.value

    @property
    def type(self) -> ChannelType:
        """:class:`ChannelType`: 频道的 QQ 类型。"""
        return ChannelType.category

    @property
    def channels(self) -> List[GuildChannelType]:
        def comparator(channel):
            return not isinstance(channel, TextChannel), channel.position

        ret = [c for c in self.guild.channels if c.category_id == self.id]
        ret.sort(key=comparator)
        return ret

    @property
    def text_channels(self) -> List[TextChannel]:
        ret = [c for c in self.guild.channels if c.category_id == self.id and isinstance(c, TextChannel)]
        ret.sort(key=lambda c: (c.position, c.id))
        return ret

    @property
    def voice_channels(self) -> List[VoiceChannel]:
        ret = [c for c in self.guild.channels if c.category_id == self.id and isinstance(c, VoiceChannel)]
        ret.sort(key=lambda c: (c.position, c.id))
        return ret

    @property
    def live_channels(self) -> List[LiveChannel]:
        ret = [c for c in self.guild.channels if c.category_id == self.id and isinstance(c, LiveChannel)]
        ret.sort(key=lambda c: (c.position, c.id))
        return ret

    @property
    def app_channels(self) -> List[AppChannel]:
        ret = [c for c in self.guild.channels if c.category_id == self.id and isinstance(c, AppChannel)]
        ret.sort(key=lambda c: (c.position, c.id))
        return ret

    @property
    def thread_channels(self) -> List[ThreadChannel]:
        ret = [c for c in self.guild.channels if c.category_id == self.id and isinstance(c, ThreadChannel)]
        ret.sort(key=lambda c: (c.position, c.id))
        return ret


class PartialMessageable(abc.Messageable, Hashable):
    def __init__(self, state: ConnectionState, id: int, type: Optional[ChannelType] = None):
        self._state: ConnectionState = state
        self._channel: Object = Object(id=id)
        self.id: int = id
        self.type: Optional[ChannelType] = type

    async def _get_channel(self) -> Tuple[Object, bool]:
        return self._channel, True

    def get_partial_message(self, message_id: int, /) -> PartialMessage:
        from .message import PartialMessage

        return PartialMessage(channel=self, id=message_id)


def _guild_channel_factory(channel_type: int):
    value = try_enum(ChannelType, channel_type)
    if value is ChannelType.text:
        return TextChannel, value
    elif value is ChannelType.voice:
        return VoiceChannel, value
    elif value is ChannelType.category:
        return CategoryChannel, value
    elif value is ChannelType.live:
        return LiveChannel, value
    elif value is ChannelType.app:
        return AppChannel, value
    elif value is ChannelType.thread:
        return ThreadChannel, value
    else:
        return None, value


def _channel_factory(channel_type: int):
    cls, value = _guild_channel_factory(channel_type)
    return cls, value


DMC = TypeVar('DMC', bound='DMChannel')


class DMChannel(abc.Messageable, Hashable):
    """代表一个QQ私信子频道。
    
    .. container:: operations
        .. describe:: x == y
            检查两个子频道是否相等。
        .. describe:: x != y
            检查两个子频道是否不相等。
        .. describe:: hash(x)
            返回子频道的哈希值。
        .. describe:: str(x)
            返回子频道的字符串表示形式

    Attributes
    ----------
    recipient: Optional[:class:`User`]
        在私信子频道中参与的用户。如果通过网关接收此子频道，则接收者信息可能并不总是可用。
    me: :class:`ClientUser`
        代表你自己的用户。
    id: :class:`int`
        私信会话关联的子频道 id
    channel_id: :class:`int`
        垃圾资讯，无视即可，官方不知道在搞什么jb东西
    """

    __slots__ = ('id', 'recipient', 'me', 'channel_id', '_state')

    def __init__(self, *, me: ClientUser, state: ConnectionState, data: DMChannelPayload, recipients: User):
        self._state: ConnectionState = state
        self.recipient: Optional[User] = recipients
        self.me: ClientUser = me
        self.id: int = int(data['guild_id'])
        self.channel_id: int = int(data['channel_id'])

    async def _get_channel(self):
        return self, True

    def __str__(self) -> str:
        if self.recipient:
            return f'与 {self.recipient} 的直接消息'
        return '与未知用户的直接消息'

    def __repr__(self) -> str:
        return f'<DMChannel id={self.id} guild_id={self.channel_id} recipient={self.recipient!r}>'

    @classmethod
    def _from_message(cls: Type[DMC], state: ConnectionState, channel_id: int, guild_id: int) -> DMC:
        self: DMC = cls.__new__(cls)
        self._state = state
        self.channel_id = channel_id
        self.id = guild_id
        self.recipient = None
        # state.user won't be None here
        self.me = state.user  # type: ignore
        return self

    @property
    def type(self) -> ChannelType:
        """:class:`ChannelType`: 频道的 QQ 类型。"""
        return ChannelType.private

    def get_partial_message(self, message_id: int, /) -> PartialMessage:
        """从消息 ID 创建一个 :class:`PartialMessage` 。
        如果您想处理消息并且只拥有其 ID 而不进行不必要的 API 调用，这将非常有用。

        Parameters
        ------------
        message_id: :class:`int`
            要为其创建部分消息的消息 ID。

        Returns
        ---------
        :class:`PartialMessage`
            部分消息。
        """

        from .message import PartialMessage

        return PartialMessage(channel=self, id=message_id)
